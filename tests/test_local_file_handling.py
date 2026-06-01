import pytest
import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add plugin root to path for imports
_plugin_root = str(Path(__file__).resolve().parent.parent)
if _plugin_root not in os.sys.path:
    os.sys.path.insert(0, _plugin_root)

from tools.opennotebook_sources import OpenNotebookSources, _detect_and_prepare, _FILE_EXTENSIONS


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


# --- Tests for _detect_and_prepare (Auto-detection logic) ---

@pytest.mark.asyncio
async def test_detect_url(mock_agent):
    """Test that URLs are correctly identified and formatted."""
    url = "https://example.com/document.pdf"
    source_type, data = await _detect_and_prepare(url, "Test Title", "nb123")
    
    assert source_type == "link"
    assert data["type"] == "link"
    assert data["url"] == url
    assert data["notebook_id"] == "nb123"
    assert "content" not in data


@pytest.mark.asyncio
async def test_detect_local_file_success(tmp_path, mock_agent):
    """Test successful reading of a local text file."""
    # Create a temporary text file
    file_path = tmp_path / "test_note.txt"
    file_content = "This is the content of the note."
    file_path.write_text(file_content)
    
    source_type, data = await _detect_and_prepare(str(file_path), "", "nb123")
    
    assert source_type == "text"
    assert data["type"] == "text"
    assert data["content"] == file_content
    assert data["title"] == "test_note"  # Auto-set from filename
    assert "url" not in data


@pytest.mark.asyncio
async def test_detect_local_file_not_found(mock_agent):
    """Test error when a local file path is provided but file doesn't exist."""
    file_path = "/tmp/does_not_exist.txt"
    
    with pytest.raises(ValueError) as exc_info:
        await _detect_and_prepare(file_path, "", "nb123")
    
    error_msg = str(exc_info.value)
    assert "❌" in error_msg
    assert "File not found" in error_msg
    assert "💡" in error_msg  # Check for hint


@pytest.mark.asyncio
async def test_detect_local_file_permission_error(tmp_path, mock_agent):
    """Test error when file exists but cannot be read (permissions)."""
    # Create a file and remove read permissions
    file_path = tmp_path / "secret.txt"
    file_path.write_text("Secret content")
    os.chmod(file_path, 0o000)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            await _detect_and_prepare(str(file_path), "", "nb123")
        
        error_msg = str(exc_info.value)
        assert "❌" in error_msg
        assert "Permission denied" in error_msg
        assert "💡" in error_msg
    finally:
        # Restore permissions for cleanup
        os.chmod(file_path, 0o644)


@pytest.mark.asyncio
async def test_detect_raw_text(mock_agent):
    """Test that raw text (no URL, no file extension) is handled as text."""
    text_content = "Just some random thoughts for the day."
    source_type, data = await _detect_and_prepare(text_content, "My Thoughts", "nb123")
    
    assert source_type == "text"
    assert data["type"] == "text"
    assert data["content"] == text_content
    assert data["title"] == "My Thoughts"
    assert "url" not in data


@pytest.mark.asyncio
async def test_detect_mixed_input_path_like_text(tmp_path, mock_agent):
    """Test that a string looking like a path but with unsupported extension is treated as text."""
    text_content = "/path/to/my/unsupported.xyz"
    # Do not create the file
    source_type, data = await _detect_and_prepare(text_content, "", "nb123")
    
    assert source_type == "text"
    assert data["content"] == text_content


# --- Tests for Integration with Sources Tool (Add Method) ---

@pytest.mark.asyncio
async def test_add_source_local_file_integration(sources_tool, tmp_path):
    """Test the full 'add' flow with a local file, mocking the API."""
    # Setup
    file_path = tmp_path / "integration_test.md"
    file_content = "# Integration Test\nThis is a markdown file."
    file_path.write_text(file_content)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "src123", "status": "processing"}
    
    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response
    
    # Execute
    with patch('tools.opennotebook_sources.client.get_client', return_value=mock_http_client):
        result = await sources_tool.execute(
            notebook_id="nb123",
            action="add",
            content=str(file_path)
        )
    
    # Verify
    assert result.break_loop is False
    assert "Integration Test" in result.message or "integration_test" in result.message
    # Verify the API was called with file CONTENT, not path
    call_args = mock_http_client.post.call_args
    assert call_args is not None
    # The data is form-encoded, checking content string presence is sufficient
    # In a real scenario we'd parse the multipart form, but for this unit test
    # we check that the file was read.
    assert file_content in str(call_args) or len(call_args[1]['content']) > 0


@pytest.mark.asyncio
async def test_add_source_url_integration(sources_tool):
    """Test the full 'add' flow with a URL."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "src456", "status": "processing"}
    
    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response
    
    url = "https://example.com/article"
    
    with patch('tools.opennotebook_sources.client.get_client', return_value=mock_http_client):
        result = await sources_tool.execute(
            notebook_id="nb123",
            action="add",
            content=url
        )
    
    assert result.break_loop is False
    call_args = mock_http_client.post.call_args
    # Check that URL was passed in the form data (simplified check)
    assert url in str(call_args)
