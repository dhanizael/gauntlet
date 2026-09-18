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

- [ ] The cast transcript matches `uv run gauntlet demo`.
- [ ] README diagram text matches the demo's causal story.
- [ ] Case-study metrics cite checked-in evidence and disclose limits.
