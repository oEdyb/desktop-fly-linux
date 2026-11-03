#!/bin/bash
# Launch desktopfly with a clean environment.
# See tools/desnap.sh — snap-packaged editors may export conflicting GTK vars.
cd "$(dirname "$0")"
PYTHON=python3
if [ -x .venv-brain/bin/python ]; then
    PYTHON=.venv-brain/bin/python
fi
exec ./tools/desnap.sh "$PYTHON" -m desktopfly "$@"
