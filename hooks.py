"""
Open Notebook Plugin — Lifecycle Hooks

Replaces execute.py with framework-native hooks.py for setup,
configuration, and uninstall lifecycle management.

Hooks are called by helpers/plugins.py via call_plugin_hook().
"""

import subprocess
import sys
import urllib.request


DEFAULT_API_URL = "http://host.docker.internal:5055"


def _check_url(url: str, timeout: int = 5) -> bool:
    """Check if a URL is reachable."""
    try:
        resp = urllib.request.urlopen(f"{url}/api/transformations", timeout=timeout)
        return resp.status == 200
    except Exception:
        return False


def agent_init(default=None, agent=None, **kwargs):
    """Called when an agent initializes. Checks backend connectivity and dependencies.

    Replaces the setup logic from execute.py, running automatically on agent start.
    """
    import os

    # 1. Check backend connectivity
    api_url = os.environ.get("OPEN_NOTEBOOK_API_URL", DEFAULT_API_URL)

    if _check_url(api_url):
        backend_ok = True
    elif _check_url("http://localhost:5055"):
        backend_ok = True
    else:
        backend_ok = False

    # 2. Verify httpx is available (should be in requirements)
    try:
        import httpx  # noqa: F401
        deps_ok = True
    except ImportError:
        deps_ok = False

    # 3. Store health state in agent context for tools/extensions
    if agent and hasattr(agent, 'context') and hasattr(agent.context, 'data'):
        agent.context.data['on_backend_reachable'] = backend_ok
        agent.context.data['on_deps_installed'] = deps_ok

    # 4. Print status for logs
    from helpers.print_style import PrintStyle
    if backend_ok and deps_ok:
        PrintStyle(font_color="green", padding=True).print(
            f"Open Notebook: connected to {api_url}"
        )
    elif not backend_ok:
        PrintStyle(font_color="yellow", padding=True).print(
            f"Open Notebook: backend not reachable at {api_url}. "
            "Make sure Open Notebook is running."
        )
    if not deps_ok:
        PrintStyle(font_color="yellow", padding=True).print(
            "Open Notebook: httpx not found. Install with: pip install httpx>=0.24.0"
        )

    return default


def uninstall(**kwargs):
    """Called when the plugin is uninstalled. Clean up any persistent state.

    The plugin stores no persistent state outside of agent context data,
    so this is a no-op for now. Kept for future extensibility.
    """
    from helpers.print_style import PrintStyle
    PrintStyle(font_color="green", padding=True).print(
        "Open Notebook: uninstalled successfully."
    )
    return None


def get_plugin_config(default=None, agent=None, **kwargs):
    """Allow custom config resolution if needed.

    Currently returns the default config resolution. Kept for future
    extensibility (e.g., dynamic API URL based on agent profile).
    """
    return default
