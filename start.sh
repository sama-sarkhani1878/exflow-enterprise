#!/bin/bash
# ExFlow Enterprise startup script
# Fixes PIL/Heremes path conflict
cd "$(dirname "$0")"

# Get the project's venv site-packages
VENV_SITE=$(python3 -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")

# Start Streamlit with only the project venv in PYTHONPATH
PYTHONPATH="$VENV_SITE" exec python3 -m streamlit run app.py --server.port 8503
