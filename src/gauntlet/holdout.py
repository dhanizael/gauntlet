"""holdout — provably-fresh holdout generation + the retirement ledger.

Implements docs/HOLDOUT_DESIGN.md literally (pre-registered before code,
like GRADE_DESIGN.md). One question: after a leak, "regenerate" must mean
PROVABLY fresh — not "hope the new one is different".

Mechanisms (frozen):
  families   private-side JSON templates, typed slots, {{ name }} rendering
  PRNG       counter-mode SHA-256 — byte-stable across Python versions and
             platforms, forever (random.Random is NOT; provenance would rot)
  seeds      "<family_id>:<counter>", consumed in order, never reused
  gate       dual: exact slot-digest collision intra-family (boilerplate
             makes text distance meaningless there); >=2 matched shingles
             cross-family against the manifest
  ledger     append-only, hash-chained JSONL, 0600 — generated / skipped /
             retired; the death record that proves a seed stays dead
  verify     chain re-walk + manifest<->ledger reconciliation + --deep
             re-derivation (template hash and content hash must match)

The ledger contains hashes and ids, never slot values or prompt text: a
leaked ledger leaks nothing (redaction contract, ADR-0002). Everything
here is private-side (ADR-0007).
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .envfp import sha_file
from .fingerprint import normalize, sha256_hex, shingle_set
from .manifest import InstanceRecord, add_instance, load_manifest, retire_instance

SCHEMA = 1
GENESIS = "0" * 64
SLOT_KINDS = {"int", "int_list", "choice", "permutation"}
TEMPLATE_REF = re.compile(r"\{\{\s*(\w+)\s*\}\}")
FAMILY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ENUMERABLE_BELOW = 10_000
CROSS_FAMILY_MIN_SHINGLES = 2  # guard's trace threshold
ATTEMPT_BUDGET_FACTOR = 10


class HoldoutUsageError(RuntimeError):
    """Operator/template error — exit code 2, nothing written."""


class HoldoutIntegrityError(RuntimeError):
    """Gate exhausted or integrity failure — exit code 1."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class SeedStream:
    """Counter-mode SHA-256 PRNG: block_i = sha256(key + ':' + i), consumed
    byte-wise; uniform ints via rejection sampling (no modulo bias)."""

    def __init__(self, key: str) -> None:
        self._key = key.encode()
        self._counter = 0
        self._buf = b""

    def _take(self, n: int) -> bytes:
        while len(self._buf) < n:
            digest = hashlib.sha256(self._key + b":" + str(self._counter).encode()).digest()
            self._buf += digest
            self._counter += 1
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def below(self, n: int) -> int:
        if n <= 0:
            raise ValueError("below() needs n >= 1")
        limit = (1 << 64) // n * n
        while True:
            x = int.from_bytes(self._take(8), "little")
            if x < limit:
                return x % n

    def int_in(self, lo: int, hi: int) -> int:
        return lo + self.below(hi - lo + 1)

    def choice(self, seq: list) -> object:
        return seq[self.below(len(seq))]

    def shuffle(self, seq: list) -> list:
        out = list(seq)
        for i in range(len(out) - 1, 0, -1):
            j = self.below(i + 1)
            out[i], out[j] = out[j], out[i]
        return out


# ---------------------------------------------------------------- family


def load_family(path: Path) -> dict:
    try:
        family = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise HoldoutUsageError(f"{path}: invalid JSON ({exc})") from exc
    if not isinstance(family, dict) or family.get("schema") != SCHEMA:
        raise HoldoutUsageError(f"{path}: family schema must be {SCHEMA}")
    return family


def validate_family(family: dict, family_dir: Path) -> None:
    if family.get("schema") != SCHEMA:
        raise HoldoutUsageError(f"family schema must be {SCHEMA}")
    fid = family.get("id")
    if not isinstance(fid, str) or not FAMILY_ID_RE.match(fid):
        raise HoldoutUsageError("family id must match [a-z0-9-]+")
    prompt = family.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise HoldoutUsageError("family prompt must be a non-empty string")
    slots = family.get("slots")
    if not isinstance(slots, dict) or not slots:
        raise HoldoutUsageError("family needs a non-empty slots object")
    for name, spec in slots.items():
        if not isinstance(spec, dict) or spec.get("kind") not in SLOT_KINDS:
            raise HoldoutUsageError(f"slot {name!r}: kind must be one of {sorted(SLOT_KINDS)}")
        kind = spec["kind"]
        if kind in ("int", "int_list"):
            lo, hi = spec.get("min"), spec.get("max")
            if not (isinstance(lo, int) and isinstance(hi, int) and lo <= hi):
                raise HoldoutUsageError(f"slot {name!r}: needs integer min <= max")
            if kind == "int_list" and not (
                isinstance(spec.get("count"), int) and spec["count"] >= 1
            ):
                raise HoldoutUsageError(f"slot {name!r}: int_list needs count >= 1")
        if kind in ("choice", "permutation"):
            of = spec.get("of")
            if not isinstance(of, list) or not of:
                raise HoldoutUsageError(f"slot {name!r}: needs a non-empty 'of' list")
    fixtures = family.get("fixtures", {})
    if not isinstance(fixtures, dict):
        raise HoldoutUsageError("fixtures must be an object of filename -> template")
    for fname in fixtures:
        if "/" in fname or fname.startswith("."):
            raise HoldoutUsageError(f"fixture name must be a plain filename: {fname!r}")
    refs = TEMPLATE_REF.findall(prompt) + [
        ref for tmpl in fixtures.values() for ref in TEMPLATE_REF.findall(str(tmpl))
    ]
    for ref in refs:
        if ref not in slots:
            raise HoldoutUsageError(f"template references unknown slot {ref!r}")
    answer_cmd = family.get("answer_cmd")
    if answer_cmd is not None:
        if not (
            isinstance(answer_cmd, list)
            and answer_cmd
            and all(isinstance(a, str) for a in answer_cmd)
        ):
            raise HoldoutUsageError("answer_cmd must be a non-empty argv list of strings")
        script = Path(answer_cmd[1]) if len(answer_cmd) > 1 else None
        if (
            script is not None
            and script.suffix == ".py"
            and not script.is_absolute()
            and not (family_dir / script).exists()
        ):
            raise HoldoutUsageError(f"answer_cmd script not found: {family_dir / script}")
        verifier = family.get("verifier") or {}
        if not isinstance(verifier, dict) or verifier.get("type") != "expect_file":
            raise HoldoutUsageError("answer_cmd requires verifier.type == 'expect_file'")


def cardinality(family: dict) -> int:
    total = 1
    for spec in family["slots"].values():
        kind = spec["kind"]
        if kind == "int":
            space = spec["max"] - spec["min"] + 1
        elif kind == "int_list":
            space = (spec["max"] - spec["min"] + 1) ** spec["count"]
        elif kind == "choice":
            space = len(spec["of"])
        else:  # permutation
            space = 1
            for i in range(2, len(spec["of"]) + 1):
                space *= i
        total *= space
    return total


def derive_slots(family: dict, key: str) -> dict:
    """Slot values from the version-stable stream; iteration order is sorted
    slot names so derivation is independent of JSON key order."""
    stream = SeedStream(key)
    values: dict = {}
    for name in sorted(family["slots"]):
        spec = family["slots"][name]
        kind = spec["kind"]
        if kind == "int":
            values[name] = stream.int_in(spec["min"], spec["max"])
        elif kind == "int_list":
            values[name] = [stream.int_in(spec["min"], spec["max"]) for _ in range(spec["count"])]
        elif kind == "choice":
            values[name] = stream.choice(list(spec["of"]))
        else:
            values[name] = stream.shuffle(list(spec["of"]))
    return values


def render(template: str, values: dict, slots: dict | None = None) -> str:
    def sub(match: re.Match) -> str:
        name = match.group(1)
        value = values[name]
        if isinstance(value, list):
            sep = (slots or {}).get(name, {}).get("sep", " ")
            return sep.join(str(v) for v in value)
        return str(value)

    return TEMPLATE_REF.sub(sub, template)


def slot_digest(values: dict) -> str:
    canonical = json.dumps(values, sort_keys=True, separators=(",", ":"))
    return sha256_hex(canonical.encode())


# ---------------------------------------------------------------- ledger


def ledger_path_for(private_dir: Path, family_id: str) -> Path:
    return Path(private_dir) / f"{family_id}.ledger.jsonl"


def _serialize(entry: dict) -> bytes:
    return (json.dumps(entry, sort_keys=True) + "\n").encode()


def load_ledger(path: Path) -> list[tuple[dict, bytes]]:
    """All entries as (entry, raw_line). Raises HoldoutIntegrityError on a broken
    chain — a tampered ledger is never silently readable."""
    if not path.exists():
        return []
    entries: list[tuple[dict, bytes]] = []
    prev = GENESIS
    for i, raw in enumerate(path.read_bytes().splitlines(keepends=True)):
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HoldoutIntegrityError(f"ledger line {i + 1}: invalid JSON") from exc
        if entry.get("prev") != prev:
            raise HoldoutIntegrityError(
                f"ledger line {i + 1}: broken chain (seq {entry.get('seq')})"
            )
        prev = hashlib.sha256(raw).hexdigest()
        entries.append((entry, raw))
    return entries


def append_entry(path: Path, entry: dict) -> str:
    """Append one hash-chained entry; returns the sha256 of the written line.
    Refuses to append on top of a broken chain (load_ledger raises first)."""
    entries = load_ledger(path)
    prev = hashlib.sha256(entries[-1][1]).hexdigest() if entries else GENESIS
    line = _serialize({**entry, "prev": prev})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as fh:
        fh.write(line)
    path.chmod(0o600)
    return hashlib.sha256(line).hexdigest()


def verify_chain(path: Path) -> list[str]:
    try:
        load_ledger(path)
    except HoldoutIntegrityError as exc:
        return [str(exc)]
    return []


# ------------------------------------------------------- artifact building


def _write_artifacts(family: dict, instance_id: str, values: dict, out_dir: Path) -> list[Path]:
    """prompt.txt + fixtures/ (NOT task.json: answer_cmd output is derived
    metadata, excluded from the deterministic content digest by design)."""
    idir = Path(out_dir) / instance_id
    (idir / "fixtures").mkdir(parents=True, exist_ok=True)
    files = [idir / "prompt.txt"]
    (idir / "prompt.txt").write_text(render(family["prompt"], values, family["slots"]))
    for fname, tmpl in family.get("fixtures", {}).items():
        fpath = idir / "fixtures" / fname
        fpath.write_text(render(str(tmpl), values, family["slots"]))
        files.append(fpath)
    return files


def _content_digest(files: list[Path]) -> str:
    root = files[0].parent
    lines = [f"{f.relative_to(root)}:{sha_file(f)}" for f in sorted(files)]
    return sha256_hex("\n".join(lines).encode())


def _derive_equals(family: dict, family_dir: Path, values: dict) -> str | None:
    """Run answer_cmd with cwd = the family file's directory, so relative
    script paths mean the same thing here as in validate_family."""
    answer_cmd = family.get("answer_cmd")
    if not answer_cmd:
        return None
    try:
        proc = subprocess.run(
            answer_cmd,
            cwd=family_dir,
            input=json.dumps(values).encode(),
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HoldoutUsageError(f"answer_cmd failed to run: {exc}") from exc
    if proc.returncode != 0:
        detail = proc.stderr.decode(errors="replace")[:200]
        raise HoldoutIntegrityError(f"answer_cmd exited {proc.returncode}: {detail}")
    return proc.stdout.decode().strip()


# ------------------------------------------------------------------ gate


def _cross_check(
    manifest: list[InstanceRecord], entries: list[tuple[dict, bytes]], fid: str
) -> list[str]:
    ledger_retired = {e["instance"] for e, _ in entries if e["kind"] == "retired"}
    prefix = f"{fid}:"
    manifest_retired = {r.instance for r in manifest if r.retired and r.seed.startswith(prefix)}
    return [
        f"divergence: instance {instance} retired in manifest but not in ledger"
        for instance in sorted(manifest_retired - ledger_retired)
    ] + [
        f"divergence: instance {instance} retired in ledger but active in manifest"
        for instance in sorted(ledger_retired - manifest_retired)
    ]


# ------------------------------------------------------------ operations


def _resolve_ledger(private_dir: Path, fid: str, ledger: Path | None) -> Path:
    return Path(ledger) if ledger else ledger_path_for(private_dir, fid)


def _load_manifest_checked(manifest_path: Path) -> list[InstanceRecord]:
    if not manifest_path.exists():
        raise HoldoutUsageError(f"manifest not found: {manifest_path} (create the file first)")
    return load_manifest(manifest_path)


def _next_counter(counters_used: set[str], fid: str) -> int:
    n = 0
    while f"{fid}:{n}" in counters_used:
        n += 1
    return n


def generate(  # noqa: PLR0913 — the parameters mirror the CLI flags one to one
    family_path: Path,
    manifest_path: Path,
    private_dir: Path,
    *,
    count: int = 1,
    seed: str | None = None,
    ledger: Path | None = None,
) -> list[dict]:
    if count < 1:
        raise HoldoutUsageError("count must be >= 1")
    family = load_family(family_path)
    validate_family(family, family_path.parent)
    fid = family["id"]
    manifest = _load_manifest_checked(manifest_path)
    lpath = _resolve_ledger(private_dir, fid, ledger)
    entries = load_ledger(lpath)  # broken chain => HoldoutIntegrityError, nothing written
    problems = _cross_check(manifest, entries, fid)
    if problems:
        raise HoldoutIntegrityError(
            "; ".join(problems) + " — run 'holdout verify' and reconcile first"
        )

    counters_used = {e["seed"] for e, _ in entries if e["kind"] in ("generated", "skipped")}
    used_slot_digests = {e["slot_sha256"] for e, _ in entries if e["kind"] == "generated"}
    template_sha = sha256_hex(family_path.read_bytes())
    known_instances = {r.instance for r in manifest} | {
        e["instance"] for e, _ in entries if e["kind"] in ("generated", "retired")
    }

    budget = ATTEMPT_BUDGET_FACTOR * count + 10
    summaries: list[dict] = []
    pending: str | None = seed
    n = _next_counter(counters_used, fid)
    produced = 0
    while produced < count:
        if budget <= 0:
            raise HoldoutIntegrityError(
                f"freshness gate exhausted after {ATTEMPT_BUDGET_FACTOR * count + 10} "
                "attempts; family entropy too low for this count"
            )
        budget -= 1
        if pending is not None:
            seed_str, pending = pending, None
        else:
            seed_str = f"{fid}:{n}"
            while seed_str in counters_used:
                n += 1
                seed_str = f"{fid}:{n}"
        if seed_str in counters_used:
            raise HoldoutUsageError(f"seed {seed_str!r} is already consumed (ledger)")
        counters_used.add(seed_str)

        values = derive_slots(family, f"{fid}/{seed_str}")
        digest = slot_digest(values)
        if digest in used_slot_digests:
            append_entry(
                lpath,
                {"kind": "skipped", "seed": seed_str, "reason": "slot-collision", "at": _now()},
            )
            n += 1
            continue
        prompt = render(family["prompt"], values, family["slots"])
        prompt_shingles = shingle_set(normalize(prompt))
        prefix = f"{fid}:"
        overlapped = any(
            len(prompt_shingles & rec.shingles) >= CROSS_FAMILY_MIN_SHINGLES
            for rec in manifest
            if not rec.seed.startswith(prefix)
        )
        if overlapped:
            append_entry(
                lpath,
                {
                    "kind": "skipped",
                    "seed": seed_str,
                    "reason": "cross-family-overlap",
                    "at": _now(),
                },
            )
            n += 1
            continue

        instance_id = f"{fid}-{n}"
        if instance_id in known_instances:
            raise HoldoutUsageError(
                f"instance {instance_id!r} already exists "
                "(manifest/ledger divergence? run 'holdout verify')"
            )
        with tempfile.TemporaryDirectory() as td:
            files = _write_artifacts(family, instance_id, values, Path(td))
            staged = Path(td) / instance_id
            real_dir = Path(private_dir) / instance_id
            if real_dir.exists():
                raise HoldoutUsageError(f"instance directory already exists: {real_dir}")
            real_dir.parent.mkdir(parents=True, exist_ok=True)
            promoted: list[Path] = []
            for f in files:
                dst = real_dir / f.relative_to(staged)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(f.read_text())
                promoted.append(dst)
            content = _content_digest(promoted)
        task: dict = {
            "id": instance_id,
            "prompt": prompt,
            "verifier": dict(family.get("verifier") or {}),
        }
        equals = _derive_equals(family, family_path.parent, values)
        if equals is not None:
            task["verifier"]["equals"] = equals
        (real_dir / "task.json").write_text(json.dumps(task, indent=1, sort_keys=True) + "\n")

        rec = add_instance(manifest_path, instance_id, seed_str, promoted)
        manifest.append(rec)
        known_instances.add(instance_id)
        used_slot_digests.add(digest)
        append_entry(
            lpath,
            {
                "kind": "generated",
                "seed": seed_str,
                "instance": instance_id,
                "template_sha256": template_sha,
                "content_sha256": content,
                "slot_sha256": digest,
                "at": _now(),
            },
        )
        summaries.append(
            {"instance": instance_id, "seed": seed_str, "dir": str(real_dir), "task": task}
        )
        produced += 1
        n += 1

    card = cardinality(family)
    if card < ENUMERABLE_BELOW:
        summaries.append(
            {
                "warning": (
                    f"enumerable family: cardinality {card} < {ENUMERABLE_BELOW} — "
                    "an agent could enumerate every instance; widen the slot pools"
                )
            }
        )
    return summaries


def retire(
    family_path: Path,
    instance: str,
    manifest_path: Path,
    private_dir: Path,
    *,
    ledger: Path | None = None,
) -> dict:
    """Frozen order: manifest FIRST (guard reads the manifest — stop the
    bleed immediately), ledger second. A crash between the two is a real
    state that 'holdout verify' names from either side."""
    family = load_family(family_path)
    fid = family["id"]
    _load_manifest_checked(manifest_path)  # fail fast with exit-2 clarity
    lpath = _resolve_ledger(private_dir, fid, ledger)
    entries = load_ledger(lpath)
    manifest_retired = retire_instance(manifest_path, instance)
    generated = any(e["kind"] == "generated" and e["instance"] == instance for e, _ in entries)
    if not manifest_retired and not generated:
        raise HoldoutUsageError(f"unknown instance {instance!r} in manifest or ledger")
    ledger_retired = False
    if generated:
        append_entry(
            lpath, {"kind": "retired", "instance": instance, "reason": "leak", "at": _now()}
        )
        ledger_retired = True
    return {
        "instance": instance,
        "manifest_retired": manifest_retired,
        "ledger_retired": ledger_retired,
    }


def verify(
    family_path: Path,
    manifest_path: Path,
    private_dir: Path,
    *,
    deep: bool = False,
    ledger: Path | None = None,
) -> list[str]:
    family = load_family(family_path)
    fid = family["id"]
    manifest = _load_manifest_checked(manifest_path)
    lpath = _resolve_ledger(private_dir, fid, ledger)
    problems = verify_chain(lpath)
    entries: list[tuple[dict, bytes]] = []
    if not problems:
        entries = load_ledger(lpath)
        problems += _cross_check(manifest, entries, fid)
        if deep:
            template_sha = sha256_hex(family_path.read_bytes())
            for entry, _ in entries:
                if entry["kind"] != "generated":
                    continue
                if entry["template_sha256"] != template_sha:
                    problems.append(
                        f"deep: template changed since {entry['instance']} was generated"
                    )
                    continue
                values = derive_slots(family, f"{fid}/{entry['seed']}")
                with tempfile.TemporaryDirectory() as td:
                    files = _write_artifacts(family, entry["instance"], values, Path(td))
                    redone = _content_digest(files)
                if redone != entry["content_sha256"]:
                    problems.append(f"deep: instance {entry['instance']} drifted (hash mismatch)")
    return problems


def status(
    family_path: Path,
    manifest_path: Path,
    private_dir: Path,
    *,
    ledger: Path | None = None,
) -> dict:
    family = load_family(family_path)
    fid = family["id"]
    manifest = _load_manifest_checked(manifest_path)
    lpath = _resolve_ledger(private_dir, fid, ledger)
    entries = load_ledger(lpath)
    generated = [e for e, _ in entries if e["kind"] == "generated"]
    skipped = [e for e, _ in entries if e["kind"] == "skipped"]
    retired = [e for e, _ in entries if e["kind"] == "retired"]
    counters_used = {e["seed"] for e, _ in entries if e["kind"] in ("generated", "skipped")}
    card = cardinality(family)
    warnings = _cross_check(manifest, entries, fid)
    if card < ENUMERABLE_BELOW:
        warnings.append(
            f"enumerable family: cardinality {card} < {ENUMERABLE_BELOW} — widen the slot pools"
        )
    template_sha = sha256_hex(family_path.read_bytes())
    if generated and generated[-1]["template_sha256"] != template_sha:
        warnings.append("template changed since last generation (deep provenance affected)")
    return {
        "id": fid,
        "generated": len(generated),
        "skipped": len(skipped),
        "retired": len(retired),
        "next_counter": _next_counter(counters_used, fid),
        "cardinality": card,
        "cardinality_display": "≥ 10^12" if card >= 10**12 else str(card),
        "warnings": warnings,
    }
