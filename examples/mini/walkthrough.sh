#!/usr/bin/env bash
# gauntlet mini — the whole loop on toy tasks: ~15 seconds, $0, no LLM.
# Override the binary with GAUNTLET_BIN="gauntlet" if installed as a tool.
set -euo pipefail
cd "$(dirname "$0")"
GAUNTLET_BIN=${GAUNTLET_BIN:-"uvx --from gauntlet-guard gauntlet"}
# shellcheck disable=SC2086  # GAUNTLET_BIN is intentionally word-split
g() { $GAUNTLET_BIN "$@"; }
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

echo "=== 1. the experiment: 2 toy tasks x 2 arms x 2 repeats =="
g run init "$WORK/exp" --tasks tasks.json --arms quick,careful --repeats 2

echo
echo "=== 2. run every slot (arm read from the private ledger; judges stay blind) ==="
python3 - "$WORK/exp" "$WORK/plan.tsv" <<'PY'
import json, sys
rows = []
for line in open(sys.argv[1] + "/ledger.jsonl"):
    r = json.loads(line)
    if r.get("kind") == "trial-created":
        rows.append((r["slot"], r["task"], r["arm"]))
with open(sys.argv[2], "w") as fh:
    for row in rows:
        fh.write("\t".join(row) + "\n")
PY
while IFS=$'\t' read -r slot task arm; do
  m=buggy
  [ "$arm" = "careful" ] && m=correct
  g run prep "$WORK/exp" --slot "$slot" --fixtures "fixtures-$task"
  g run exec "$WORK/exp" --slot "$slot" -- python3 "$PWD/agent.py" --method "$m"
done < "$WORK/plan.tsv"

echo
echo "=== 3. blindpack (the judge pack carries pseudonyms, not arms) ==="
g run blindpack "$WORK/exp" --out "$WORK/pack"

echo
echo "=== 4. the verdict (exit code IS the verdict) ==="
set +e
g grade "$WORK/exp" --primary careful --baseline quick
code=$?
set -e
echo "grade exit code: $code   (0 keep · 1 revert · 2 provisional · 3 integrity failure)"

echo
echo "=== 5. the memory audit: seal the tasks, then catch them if they leak ==="
python3 - "$WORK" <<'PY'
import json, pathlib, sys
w = pathlib.Path(sys.argv[1])
tasks = json.loads(pathlib.Path("tasks.json").read_text())
for t in tasks:
    (w / (t["id"] + ".txt")).write_text(t["prompt"])
(w / "notes").mkdir()
(w / "notes" / "LESSONS.md").write_text(
    "# lessons\n- " + tasks[0]["prompt"] + " ANSWER: 4\n"  # the agent 'took notes'
)
PY
g manifest add "$WORK/mf.jsonl" --instance mini-A --seed s-a "$WORK/mini-A.txt"
set +e
g guard scan "$WORK/mf.jsonl" --store "$WORK/notes"
scan_code=$?
set -e
echo "guard scan exit code: $scan_code   (1 = leakage found -> retire, regenerate)"
