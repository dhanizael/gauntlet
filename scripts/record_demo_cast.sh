#!/usr/bin/env bash
set -euo pipefail

uvx --from asciinema asciinema rec docs/assets/gauntlet-demo.cast \
  --overwrite --quiet --idle-time-limit 0.15 --cols 110 --rows 30 \
  --title "Gauntlet: memory, not intelligence" --command 'uv run gauntlet demo'
