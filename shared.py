"""
Open Notebook Plugin - Shared Helpers

Common utilities used across all tool files: date formatting,
status formatting, error handling, and asset type detection.
"""

try:
    import httpx
except ImportError:
    httpx = None
from errors import format_timeout, format_connection_error, format_http_error, format_unexpected


def format_date(date_str: str) -> str:
    """Format ISO date string to 'YYYY-MM-DD HH:MM'."""
    if not date_str:
        return "unknown"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return date_str


def format_status(status) -> str:
    """Format processing status with emoji for visual scanning."""
    if not status:
        return "✅ completed"
    status = str(status).lower()
    if status in ("completed", "done", "finished"):
        return "✅ completed"
    elif status in ("processing", "in_progress", "running"):
        return "⏳ processing"
    elif status in ("pending", "queued", "waiting"):
        return "⏳ pending"
    elif status in ("failed", "error"):
        return "❌ failed"
    return status


def get_asset_type(source: dict) -> str:
    """Extract display-friendly source type from nested asset data."""
    asset = source.get("asset")
    if isinstance(asset, dict):
        asset_type = asset.get("type", "")
        if asset_type:
            return asset_type
    return "text"


def handle_error(error: Exception, url: str) -> str:
    """Route errors through the error translator with user-friendly messages."""
    if isinstance(error, httpx.TimeoutException):
        return format_timeout("fetch from Open Notebook")
    elif isinstance(error, httpx.ConnectError):
        return format_connection_error()
    elif isinstance(error, httpx.HTTPStatusError):
        return format_http_error(error)
    else:
        return format_unexpected(error)
