"""Portable launcher for Live Meeting Copilot.

Designed for Nuitka standalone builds so end users can run without Python install.
"""

from __future__ import annotations

import os
import re
import shutil
import threading
import time
import webbrowser
from pathlib import Path


def _base_dir() -> Path:
    # In compiled mode, keep runtime files beside the executable.
    return Path(os.path.abspath(os.path.dirname(__file__)))


def _prepare_env(base_dir: Path) -> bool:
    env_path = base_dir / ".env"
    env_example = base_dir / ".env.example"

    if not env_path.exists() and env_example.exists():
        shutil.copyfile(env_example, env_path)
        print("Created .env from .env.example.")
        print("Please edit .env (AZURE_AI_SERVICES_KEY, AZURE_AI_SERVICES_REGION), then run again.")
        try:
            if os.name == "nt":
                os.startfile(str(env_path))  # type: ignore[attr-defined]
        except Exception:
            pass
        return False

    raw = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

    def _env_value(name: str) -> str:
        pattern = rf"(?mi)^\s*{re.escape(name)}\s*=\s*(.*?)\s*$"
        m = re.search(pattern, raw)
        if not m:
            return ""
        return str(m.group(1) or "").strip().strip("'\"")

    services_key = _env_value("AZURE_AI_SERVICES_KEY")
    services_region = _env_value("AZURE_AI_SERVICES_REGION")
    has_key = bool(services_key) and services_key.lower() != "your-azure-ai-services-key"
    has_region = bool(services_region)
    if not (has_key and has_region):
        print("Missing/placeholder AZURE_AI_SERVICES_KEY or AZURE_AI_SERVICES_REGION in .env.")
        print("Update .env, then run again.")
        try:
            if os.name == "nt" and env_path.exists():
                os.startfile(str(env_path))  # type: ignore[attr-defined]
        except Exception:
            pass
        return False

    return True


def _open_browser_later(url: str, delay_sec: float = 2.5) -> None:
    def _worker() -> None:
        time.sleep(delay_sec)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def main() -> int:
    base_dir = _base_dir()
    os.chdir(base_dir)

    if not _prepare_env(base_dir):
        return 1

    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    open_browser = str(os.getenv("OPEN_BROWSER", "1")).strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    url = f"http://{host}:{port}/"

    if open_browser:
        _open_browser_later(url)

    # Import after env checks to avoid startup failure before user can fix .env.
    from app.main import app
    import uvicorn

    uvicorn.run(app, host=host, port=port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
