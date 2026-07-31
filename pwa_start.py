"""
ExFlow Enterprise — PWA + Streamlit wrapper
Serves static files (manifest.json, sw.js, icons) alongside Streamlit.
"""
import os, sys, subprocess, threading

# Start a simple HTTP server for static files on port 8765
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

def serve_static():
    os.chdir(STATIC_DIR)
    import http.server
    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.HTTPServer(("0.0.0.0", 8765), handler)
    print(f"📁 Static server on :8765")
    httpd.serve_forever()

t = threading.Thread(target=serve_static, daemon=True)
t.start()

# Start Streamlit
print("🚀 Starting ExFlow Enterprise...")
os.chdir(os.path.dirname(__file__))
proc = subprocess.Popen(
    ["python3", "-m", "streamlit", "run", "app.py", "--server.port", "8503"]
)
proc.wait()
