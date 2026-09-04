"""Entry point for the `goalcoach` command.

Starts the API and web server in the background.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request

API_HOST = os.getenv("GOALCOACH_API_HOST", "127.0.0.1")
API_PORT = os.getenv("GOALCOACH_API_PORT", "8000")
WEB_PORT = os.getenv("GOALCOACH_WEB_PORT", "8501")
OLLAMA_URL = os.getenv("GOALCOACH_OLLAMA_URL", "http://localhost:11434")


def _run_python(args: list[str]) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, *args])


def _ollama_running() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_ollama() -> None:
    if _ollama_running():
        print(f"Ollama already running at {OLLAMA_URL}")
        return
    executable = shutil.which("ollama")
    if executable is None:
        print("ollama not found on PATH; skipping. Install it or start it manually.")
        return
    subprocess.Popen([executable, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Starting Ollama at {OLLAMA_URL}…")


def start_api() -> subprocess.Popen:
    return _run_python(["-m", "uvicorn", "apps.api.main:app", "--host", API_HOST, "--port", API_PORT])


def start_web() -> subprocess.Popen:
    return _run_python(["-m", "streamlit", "run", "apps/web/app.py", "--server.port", WEB_PORT])


def start_all() -> None:
    start_ollama()
    api = start_api()
    web = start_web()
    print(f"API running at http://{API_HOST}:{API_PORT}")
    print(f"Web running at http://127.0.0.1:{WEB_PORT}")
    try:
        api.wait()
    except KeyboardInterrupt:
        api.terminate()
        web.terminate()


def main() -> None:
    serve = os.getenv("GOALCOACH_SERVE", "all").lower()
    if serve == "api":
        start_api()
    elif serve == "web":
        start_web()
    else:
        start_all()


if __name__ == "__main__":
    main()
