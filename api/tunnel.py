"""Open Notebook Tunnel Discovery & Management API.

Provides runtime tunnel URL discovery for the ON store JS.
No hardcoded URLs — the store calls this on page load.

GET  /api/plugins/open_notebook/tunnel  → {"tunnel_url": "https://..."} | {"tunnel_url": null}
POST /api/plugins/open_notebook/tunnel  → {action: "start"|"stop"}

Dependencies: cloudflared binary only (no pip packages)
"""

import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path

from helpers.api import ApiHandler, Request, Response

logger = logging.getLogger("open_notebook")

TUNNEL_URL_FILE = Path("/a0/tmp/on-tunnel-url.txt")
TUNNEL_PID_FILE = Path("/a0/tmp/on-tunnel.pid")
DEFAULT_TUNNEL_TARGET = "http://host.docker.internal:5055"


def _get_tunnel_target() -> str:
    """Resolve the Open Notebook backend URL for tunnel target.

    Priority: plugin config > env var > default.
    """
    try:
        from helpers import plugins
        cfg = plugins.get_plugin_config("open_notebook") or {}
        if cfg.get("api_url"):
            return cfg["api_url"]
    except Exception:
        pass
    return os.environ.get("ON_TUNNEL_TARGET", DEFAULT_TUNNEL_TARGET)


def _find_tunnel_url_from_metrics() -> str | None:
    """Check cloudflared metrics endpoint for the tunnel URL."""
    import urllib.request
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:20241/metrics", timeout=2)
        for line in resp.read().decode().splitlines():
            if "trycloudflare.com" in line:
                m = re.search(r"(https://[a-z0-9-]+\.trycloudflare\.com)", line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return None


def _find_tunnel_url_from_ps() -> str | None:
    """Check running processes for cloudflared tunnel URL."""
    try:
        result = subprocess.run(
            ["ps", "-eo", "args"], capture_output=True, text=True, timeout=2
        )
        for line in result.stdout.splitlines():
            if "cloudflared" in line and "trycloudflare.com" in line:
                m = re.search(r"(https://[a-z0-9-]+\.trycloudflare\.com)", line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return None


def get_tunnel_url() -> str | None:
    """Discover the active tunnel URL from any source."""
    # 1. Check URL file (fastest, written by launcher)
    if TUNNEL_URL_FILE.is_file():
        url = TUNNEL_URL_FILE.read_text().strip()
        if url.startswith("https://"):
            return url

    # 2. Check metrics endpoint
    url = _find_tunnel_url_from_metrics()
    if url:
        TUNNEL_URL_FILE.write_text(url)
        return url

    # 3. Check process list
    url = _find_tunnel_url_from_ps()
    if url:
        TUNNEL_URL_FILE.write_text(url)
        return url

    return None


def _read_stream_for_url(stream, url_found_event):
    """Read cloudflared stderr line-by-line to find the tunnel URL."""
    for line in stream:
        text = line.decode(errors="replace") if isinstance(line, bytes) else line
        m = re.search(r"(https://[a-z0-9-]+\.trycloudflare\.com)", text)
        if m:
            url = m.group(1)
            TUNNEL_URL_FILE.write_text(url)
            logger.info("ON tunnel URL: %s", url)
            url_found_event.set()


class TunnelHandler(ApiHandler):

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_auth(cls) -> bool:
        return False  # Needed before login to set API_BASE

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")

        if action == "start":
            return await self._start()
        elif action == "stop":
            return self._stop()
        elif action == "status":
            return self._status()
        else:
            # GET / no action → return current URL
            return {"tunnel_url": get_tunnel_url()}

    def _status(self) -> dict:
        url = get_tunnel_url()
        return {
            "tunnel_url": url,
            "active": url is not None,
            "target": _get_tunnel_target(),
        }

    async def _start(self) -> dict:
        """Start a cloudflared quick tunnel."""
        existing = get_tunnel_url()
        if existing:
            return {"ok": True, "tunnel_url": existing, "message": "Already running"}

        try:
            proc = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", _get_tunnel_target()],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=False,
            )

            # Write PID
            TUNNEL_PID_FILE.write_text(str(proc.pid))

            # Wait up to 10s for the URL to appear
            url_found = asyncio.Event()
            loop = asyncio.get_event_loop()

            def reader():
                _read_stream_for_url(proc.stderr, url_found)

            await loop.run_in_executor(None, reader)

            # Give it a moment for URL discovery
            try:
                await asyncio.wait_for(url_found.wait(), timeout=10)
            except asyncio.TimeoutError:
                pass

            url = get_tunnel_url()
            if url:
                return {"ok": True, "tunnel_url": url}
            else:
                return {"ok": True, "tunnel_url": None,
                        "message": "Tunnel starting, URL not yet available"}

        except FileNotFoundError:
            return {"ok": False, "error": "cloudflared not installed"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _stop(self) -> dict:
        """Stop the cloudflared quick tunnel."""
        try:
            if TUNNEL_PID_FILE.is_file():
                pid = int(TUNNEL_PID_FILE.read_text().strip())
                os.kill(pid, 15)  # SIGTERM
                TUNNEL_PID_FILE.unlink(missing_ok=True)
        except ProcessLookupError:
            pass
        except Exception:
            pass

        # Also kill any cloudflared processes tunneling our target
        try:
            subprocess.run(["pkill", "-f", "cloudflared.*tunnel"],
                           timeout=3, capture_output=True)
        except Exception:
            pass

        TUNNEL_URL_FILE.unlink(missing_ok=True)
        return {"ok": True, "message": "Tunnel stopped"}
