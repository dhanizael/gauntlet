# Launch readiness

## Public surface

- [x] An unauthenticated visit to `https://github.com/dhanizael/gauntlet` shows the v0.3.2 README.
- [x] The visible README includes `gauntlet demo`, `run`, and `grade` as shipped.
- [x] The GitHub default branch resolves to the commit intended for launch.
- [x] `https://pypi.org/project/gauntlet-guard/` renders the same hero and current package version.
- [x] `uvx --from gauntlet-guard gauntlet demo` succeeds from a clean temporary environment.

Verified 2026-09-18 against GitHub API default branch `main` at `256fc9332087e092f7e127f044a368477f097fba`,
the unauthenticated raw README from that branch, and PyPI JSON version `0.3.2`. A clean `uvx`
run exited 0 and contained ACT 1, ACT 2, ACT 3, and "memory, not intelligence". The temporary
verification directory was `/tmp/tmp.z8K3O1M120`.

## Evidence package

- [x] The cast transcript matches `uv run gauntlet demo`.
- [x] README diagram text matches the demo's causal story.
- [x] Case-study metrics cite checked-in evidence and disclose limits.

Verified 2026-09-18 on branch `feat/public-proof-launch`: `tests/test_demo.py` compares the
checked-in transcript with executable output, `tests/test_public_assets.py` verifies the SVG and
terminal cast's public labels and secret-text exclusions, and the case study explicitly states
its evidence and limits. Regenerate the cast with `scripts/record_demo_cast.sh`.
