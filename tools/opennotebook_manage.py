"""
Open Notebook Plugin - Manage Tool

Provides connection status checking, configuration display, and notebook creation.
Methods: status, config, create
"""

import time
from helpers.tool import Tool, Response

# Import plugin modules using relative paths from plugin root
import sys
from pathlib import Path

# Add plugin root to path for imports
_plugin_root = str(Path(__file__).resolve().parent.parent)
if _plugin_root not in sys.path:
    sys.path.insert(0, _plugin_root)
_tools_dir = str(Path(__file__).resolve().parent)
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)

import config
import client
import errors
sys.modules.pop('shared', None)
from shared import format_date, format_status, get_asset_type, handle_error


class OpenNotebookManage(Tool):
    async def execute(self, **kwargs):
        method = kwargs.get("action") or self.method or "status"

        if method == "status":
            return await self._status()
        elif method == "config":
            return await self._config()
        elif method == "create":
            return await self._create(**kwargs)
        else:
            return Response(
                message=f"❌ Unknown method '{method}'. Available: status, config, create",
                break_loop=False,
            )

    async def _status(self) -> Response:
        """Check connection to Open Notebook via /health endpoint."""
        api_url = config.get_api_url(self.agent)
        health_url = f"{api_url}/health"

        try:
            start = time.monotonic()
            http_client = await client.get_client()
            response = await http_client.get(health_url)
            elapsed = time.monotonic() - start

            if response.status_code == 200:
                data = response.json()
                return Response(
                    message=(
                        f"✅ **Open Notebook is connected**\n"
                        f"\n"
                        f"| Detail | Value |\n"
                        f"|--------|-------|\n"
                        f"| Status | Connected |\n"
                        f"| Response Time | {elapsed:.2f}s |\n"
                        f"| API URL | `{api_url}` |\n"
                    ) + (
                        f"| Version | {data.get('version', 'unknown')} |\n"
                        if isinstance(data, dict) and 'version' in data
                        else ""
                    ),
                    break_loop=False,
                )
            else:
                return Response(
                    message=(
                        f"⚠️ **Open Notebook is reachable but unhealthy**\n"
                        f"\n"
                        f"| Detail | Value |\n"
                        f"|--------|-------|\n"
                        f"| Status | Unhealthy |\n"
                        f"| Response Time | {elapsed:.2f}s |\n"
                        f"| API URL | `{api_url}` |\n"
                        f"\n"
                        f"**Suggested next steps:**\n"
                        f"- Check Open Notebook logs for errors\n"
                        f"- Try again in a moment\n"
                    ),
                    break_loop=False,
                )

        except Exception as e:
            # Route through error translator
            import httpx
            if isinstance(e, httpx.TimeoutException):
                msg = errors.format_timeout("check Open Notebook health")
            elif isinstance(e, httpx.ConnectError):
                msg = errors.format_connection_error()
            else:
                msg = errors.format_unexpected(e)
            # Append configured URL for troubleshooting
            msg += f"\n**Configured API URL:** `{api_url}`"
            return Response(message=msg, break_loop=False)

    async def _config(self) -> Response:
        """Display current plugin configuration."""
        return Response(
            message=(
                f"⚙️ **Open Notebook Plugin Configuration**\n"
                f"\n"
                f"| Setting | Value |\n"
                f"|---------|-------|\n"
                f"| API URL | `{config.get_api_url(self.agent)}` |\n"
                f"| Read Only | {'Yes 🔒' if config.is_read_only(self.agent) else 'No ✏️'} |\n"
                f"| Confirmations | {'On ✅' if config.needs_confirmation(self.agent) else 'Off ⚠️'} |\n"
            ),
            break_loop=False,
        )

    async def _create(self, **kwargs) -> Response:
        """Create a new notebook with the given name and optional description.

        Args:
            name: Required. Name for the new notebook.
            description: Optional. Description for the notebook.
            confirmed: Whether the user has confirmed the creation.

        Returns:
            Response: Success message with notebook details, or a validation/
                      confirmation/error message with guidance.
        """
        # Read-only mode prevents write operations
        if config.is_read_only(self.agent):
            return Response(
                message=(
                    "⚠️ **Plugin is in read-only mode.** Cannot create notebooks.\n"
                    "Use `opennotebook_config:settings` to check or change read-only mode."
                ),
                break_loop=False,
            )

        # Validate required name parameter
        name = kwargs.get("name", "")
        if not name or not name.strip():
            return Response(
                message=(
                    "❌ **Notebook name required.**\n"
                    "Provide a name for the new notebook.\n"
                    "Example: `opennotebook_manage:create` with `name='My Research Notebook'`."
                ),
                break_loop=False,
            )

        description = kwargs.get("description", "")
        confirmed = str(kwargs.get("confirmed", "false")).lower() == "true"

        # Confirmation gate — show notebook details before creating
        if config.needs_confirmation(self.agent) and not confirmed:
            return Response(
                message=(
                    f"⚠️ **Confirm creating notebook**\n"
                    f"\n| Detail | Value |"
                    f"\n|--------|-------|"
                    f"\n| Name | `{name}` |"
                    f"\n| Description | {description or 'No description'} |"
                    f"\n\nTo confirm, call again with `confirmed: true`."
                ),
                break_loop=False,
            )

        # Build API request — POST /api/notebooks with form-encoded data
        api_url = config.get_api_url(self.agent)
        url = f"{api_url}/api/notebooks"

        try:
            http_client = await client.get_client()
            response = await http_client.post(url, json={
                "name": name,
                "description": description
            })
            response.raise_for_status()
            data = response.json()

            # Extract created notebook details from API response
            notebook_id = data.get("id", "unknown")
            notebook_name = data.get("name", name)
            notebook_desc = data.get("description", description)

            # Build response with notebook details
            lines = [
                f"✅ **Notebook created successfully**",
                "",
                f"| Detail | Value |",
                f"|--------|-------|",
                f"| ID | `{notebook_id}` |",
                f"| Name | {notebook_name} |",
                f"| Description | {notebook_desc or 'No description'} |",
            ]

            lines.append(
                f"\n💡 You can now add sources to this notebook using "
                f"`opennotebook_sources:add` with `notebook_id='{notebook_id}'`."
            )

            return Response(
                message="\n".join(lines),
                break_loop=False,
            )

        except Exception as e:
            return Response(message=handle_error(e, url), break_loop=False)