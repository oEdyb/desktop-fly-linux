#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv venv --allow-existing --python /usr/bin/python3 --system-site-packages .venv-brain
uv pip install --python .venv-brain/bin/python -r sensory-data/requirements.txt
exec .venv-brain/bin/python tools/prepare_senses.py "$@"
