"""Background process runner for local/CI test daemons (Uvicorn + Vite).

Manages process groups, ephemeral SQLite test DBs, and readiness health polling.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


class TestServerRunner:
    """Orchestrates ephemeral FastAPI backend and Vite frontend daemons."""

    def __init__(
        self,
        api_port: int = 8000,
        web_port: int = 3000,
        db_path: Path | None = None,
        log_path: Path | None = None,
    ) -> None:
        self.api_port = api_port
        self.web_port = web_port
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.db_path = db_path or (self.root_dir / ".pytest_cache" / "test_goalcoach_e2e.db")
        self.log_path = log_path or (self.root_dir / "logs" / "goalcoach.jsonl")
        self.api_proc: subprocess.Popen | None = None
        self.web_proc: subprocess.Popen | None = None
        self.api_log_file = Path("/tmp/goalcoach_test_api.log")
        self.web_log_file = Path("/tmp/goalcoach_test_web.log")

    def _is_url_reachable(self, url: str) -> bool:
        try:
            with urlopen(url, timeout=1.0) as resp:
                return resp.status in (200, 304)
        except (URLError, TimeoutError, OSError):
            return False

    def start(self, timeout_seconds: float = 60.0) -> None:
        """Start backend and frontend test daemons if not already running."""
        # 1. Start Backend if port 8000 not reachable
        api_url = f"http://127.0.0.1:{self.api_port}/health"
        if not self._is_url_reachable(api_url):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env["GOALCOACH_DATABASE_URL"] = f"sqlite:///{self.db_path.resolve()}"
            env["GOALCOACH_LOG_FILE_PATH"] = str(self.log_path.resolve())
            env["GOALCOACH_OFFLINE_LLM_FALLBACK"] = "true"
            env["PYTHONUNBUFFERED"] = "1"

            api_cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                "apps.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.api_port),
            ]
            with self.api_log_file.open("w") as api_log:
                self.api_proc = subprocess.Popen(
                    api_cmd,
                    cwd=str(self.root_dir),
                    env=env,
                    stdout=api_log,
                    stderr=api_log,
                    process_group=0,
                )

        # 2. Start Frontend if port 3000 not reachable
        web_url = f"http://127.0.0.1:{self.web_port}"
        if not self._is_url_reachable(web_url):
            web_cmd = ["npm", "run", "dev"]
            with self.web_log_file.open("w") as web_log:
                self.web_proc = subprocess.Popen(
                    web_cmd,
                    cwd=str(self.root_dir / "apps" / "web"),
                    stdout=web_log,
                    stderr=web_log,
                    process_group=0,
                )

        # 3. Wait for readiness
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout_seconds:
            api_ok = self._is_url_reachable(api_url)
            web_ok = self._is_url_reachable(web_url)
            if api_ok and web_ok:
                return
            time.sleep(0.5)

        # Failure diagnostics
        api_log_tail = ""
        web_log_tail = ""
        if self.api_log_file.exists():
            api_log_tail = self.api_log_file.read_text(errors="replace")[-500:]
        if self.web_log_file.exists():
            web_log_tail = self.web_log_file.read_text(errors="replace")[-500:]

        self.stop()
        raise TimeoutError(
            f"Servers failed to become ready within {timeout_seconds}s. "
            f"API: {self._is_url_reachable(api_url)}, Web: {self._is_url_reachable(web_url)}.\n"
            f"--- API Log Tail ---\n{api_log_tail}\n"
            f"--- Web Log Tail ---\n{web_log_tail}"
        )

    def stop(self) -> None:
        """Gracefully terminate background process groups."""
        for proc in (self.web_proc, self.api_proc):
            if proc is not None and proc.poll() is None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    proc.wait(timeout=3.0)
                except (OSError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except OSError:
                        pass
        self.api_proc = None
        self.web_proc = None
