"""
ExFlow Enterprise — Clean startup module  
Fixes PIL/hermes path conflict by removing hermes from PYTHONPATH.
"""
import os, sys, subprocess

env = os.environ.copy()

# Get system default PYTHONPATH (from python3 -c "import sys; print(':'.join(sys.path))")
import sys as _sys
default_path = [_site for _site in _sys.path if _site not in ('', os.curdir)]
default_path_str = ":".join(default_path)

# Remove hermes paths
non_hermes = [p for p in default_path_str.split(":") if "hermes" not in p.lower()]
venv_sp = "/Users/samasarkhanzadeh/MyHub/projects/exflow-enterprise/venv/lib/python3.14/site-packages"

# Make sure venv sp is present and early
if venv_sp in non_hermes:
    non_hermes.remove(venv_sp)
non_hermes.insert(0, venv_sp)

env["PYTHONPATH"] = ":".join(non_hermes)
print(f"Starting with PYTHONPATH (first 3): {env['PYTHONPATH'].split(':')[:3]}")

proc = subprocess.Popen(
    ["python3", "-m", "streamlit", "run", "app.py", "--server.port", "8503"],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    env=env
)
proc.wait()
