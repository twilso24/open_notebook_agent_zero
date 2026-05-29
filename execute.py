"""Open Notebook — Setup script.

Checks connectivity to the Open Notebook backend, installs dependencies,
and optionally starts a Cloudflare quick tunnel for remote access.
Run from A0's Plugins UI or manually: python execute.py
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


TUNNEL_URL_FILE = "/a0/tmp/on-tunnel-url.txt"
DEFAULT_API_URL = "http://host.docker.internal:5055"


def _check_url(url: str, timeout: int = 5) -> bool:
    """Check if a URL is reachable."""
    try:
        resp = urllib.request.urlopen(f"{url}/api/transformations", timeout=timeout)
        return resp.status == 200
    except Exception:
        return False


def _write_tunnel_url(url: str) -> None:
    """Write tunnel URL to discovery file."""
    Path(TUNNEL_URL_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(TUNNEL_URL_FILE).write_text(url.strip())


def _start_tunnel(target_url: str) -> str | None:
    """Start a cloudflared quick tunnel and return the public URL."""
    cloudflared = shutil.which("cloudflared")
    if not cloudflared:
        print("[ERROR] cloudflared not found. Install: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared")
        return None

    print(f"Starting Cloudflare tunnel → {target_url} ...")
    proc = subprocess.Popen(
        [cloudflared, "tunnel", "--url", target_url],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Parse the public URL from cloudflared output
    import time
    deadline = time.time() + 15
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                print("[ERROR] cloudflared exited unexpectedly")
                return None
            time.sleep(0.3)
            continue
        if "trycloudflare.com" in line:
            # Extract URL from: "|  https://xxx-yyy.trycloudflare.com"
            for part in line.split():
                if part.startswith("https://") and "trycloudflare.com" in part:
                    tunnel_url = part.rstrip("|,;")
                    _write_tunnel_url(tunnel_url)
                    print(f"[OK] Tunnel active: {tunnel_url}")
                    return tunnel_url

    print("[WARN] Could not detect tunnel URL within 15s")
    return None


def main():
    print("=" * 50)
    print("  Open Notebook — Setup")
    print("=" * 50)
    print()

    # 1. Check Python dependencies
    try:
        import websockets  # noqa: F401
        print("[OK] websockets installed.")
    except ImportError:
        print("Installing websockets...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "websockets>=12.0,<14.0"],
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            print("[OK] Installed websockets.")
        else:
            print(f"[WARN] pip install websockets failed: {result.stderr[:100]}")

    # 2. Check cloudflared
    if shutil.which("cloudflared"):
        print("[OK] cloudflared installed.")
    else:
        print("[INFO] cloudflared not found — remote tunnel won't be available.")
        print("       Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")

    # 3. Check ON backend connectivity
    api_url = os.environ.get("OPEN_NOTEBOOK_API_URL", DEFAULT_API_URL)
    print(f"\nChecking ON backend at {api_url} ...")

    if _check_url(api_url):
        print("[OK] Open Notebook backend is reachable.")
    elif _check_url("http://localhost:5055"):
        print("[OK] Open Notebook backend reachable at localhost:5055.")
        api_url = "http://localhost:5055"
    else:
        print("[WARN] Open Notebook backend not reachable.")
        print("       Make sure Open Notebook is running on the host (port 5055).")
        print("       The plugin will retry on each request.")

    # 4. Offer to start tunnel
    print()
    existing_tunnel = Path(TUNNEL_URL_FILE).read_text().strip() if Path(TUNNEL_URL_FILE).exists() else ""
    if existing_tunnel and _check_url(existing_tunnel):
        print(f"[OK] Existing tunnel active: {existing_tunnel}")
    else:
        print("No active tunnel found.")
        if shutil.which("cloudflared") and api_url:
            print("Starting tunnel for remote access...")
            tunnel_url = _start_tunnel(api_url)
            if tunnel_url:
                print(f"\n  Tunnel URL: {tunnel_url}")
                print("  This URL is auto-discovered by the Open Notebook UI.")
            else:
                print("[WARN] Tunnel failed to start. ON will use proxy fallback.")

    print()
    print("-" * 50)
    print("  Setup complete!")
    print("-" * 50)
    print()
    print("  Open A0's sidebar > Open Notebook to browse your notebooks.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
