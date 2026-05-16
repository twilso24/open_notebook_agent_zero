"""
Open Notebook Plugin - Configuration Helpers

Provides typed access to plugin settings with sensible defaults.
All tools import from this module — never access config directly.
"""

from agent import Agent
from helpers import plugins

PLUGIN_NAME = "open_notebook"


def _get_config(agent: Agent) -> dict:
    """Get the plugin config dict."""
    return plugins.get_plugin_config(PLUGIN_NAME, agent=agent) or {}


def get_api_url(agent: Agent) -> str:
    """Get the configured Open Notebook API URL."""
    return _get_config(agent).get(
        "api_url", "http://host.docker.internal:5055"
    )


def is_read_only(agent: Agent) -> bool:
    """Check if the plugin is in read-only mode."""
    return _get_config(agent).get("read_only", False)


def needs_confirmation(agent: Agent) -> bool:
    """Check if confirmations are enabled for destructive operations."""
    return _get_config(agent).get("confirmations", True)


def get_default_ask_model(agent: Agent) -> str:
    """Get the default model name for ask/RAG operations."""
    return _get_config(agent).get("default_ask_model", "")
