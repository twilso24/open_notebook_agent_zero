import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import os

# Add plugin root to path for imports
_plugin_root = str(Path(__file__).resolve().parent.parent)
if _plugin_root not in os.sys.path:
    os.sys.path.insert(0, _plugin_root)

from tools.opennotebook_sources import OpenNotebookSources
from tools.opennotebook_browse import OpenNotebookBrowse


# --- Helper to create a mock tool instance ---

@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.config = MagicMock()
    agent.config.get = MagicMock(return_value="http://localhost:5055")
    return agent


@pytest.fixture
def sources_tool(mock_agent):
    tool = OpenNotebookSources()
    tool.agent = mock_agent
    tool.method = "add"
    return tool


@pytest.fixture
def browse_tool(mock_agent):
    tool = OpenNotebookBrowse()
    tool.agent = mock_agent
    tool.method = "notebook"
    return tool


# --- Notebook Resolution Error Tests ---

@pytest.mark.asyncio
async def test_notebook_resolution_error_sources(sources_tool):
    """Test that sources:list provides a helpful error when notebook ID is invalid."""
    # Mock a 404 response from the API
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch('tools.opennotebook_sources.client.get_client', return_value=mock_http_client):
        result = await sources_tool.execute(
            notebook_id="invalid_notebook_id",
            action="list"
        )

    assert result.break_loop is False
    assert "notebook" in result.message.lower() or "not found" in result.message.lower()


@pytest.mark.asyncio
async def test_notebook_resolution_error_browse(browse_tool):
    """Test that browse:notebook provides a helpful error when notebook ID is invalid."""
    # Mock a 404 response from the API
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch('tools.opennotebook_browse.client.get_client', return_value=mock_http_client):
        result = await browse_tool.execute(
            notebook_id="fake_id_123",
            action="notebook"
        )

    assert result.break_loop is False
    assert "Notebook" in result.message and "not found" in result.message


# --- API Timeout Handling Tests ---

@pytest.mark.asyncio
async def test_api_timeout_handling(sources_tool):
    """Test that API timeouts result in a formatted error message."""
    import httpx

    mock_http_client = AsyncMock()
    mock_http_client.post.side_effect = httpx.TimeoutException("Request timed out")

    with patch('tools.opennotebook_sources.client.get_client', return_value=mock_http_client):
        result = await sources_tool.execute(
            notebook_id="nb123",
            action="list"
        )

    assert result.break_loop is False
    # The 'handle_error' function formats timeouts
    assert "timeout" in result.message.lower() or "unreachable" in result.message.lower()
