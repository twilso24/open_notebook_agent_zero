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
from tools.opennotebook_notes import OpenNotebookNotes
from tools.opennotebook_query import OpenNotebookQuery
from tools.opennotebook_podcasts import OpenNotebookPodcasts


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.config = MagicMock()
    agent.config.get = MagicMock(return_value="http://localhost:5055")
    return agent


# --- Research Workflow Integration Tests ---

@pytest.mark.asyncio
async def test_research_workflow_integration(mock_agent):
    """Test the research flow: query:find -> sources:read (optional) -> notes:create."""
    # 1. Setup Query Tool (Find)
    query_tool = OpenNotebookQuery()
    query_tool.agent = mock_agent
    query_tool.method = "find"

    # 2. Setup Notes Tool (Create)
    notes_tool = OpenNotebookNotes()
    notes_tool.agent = mock_agent
    notes_tool.method = "create"

    # Mock Query Response (Find something)
    mock_query_response = MagicMock()
    mock_query_response.status_code = 200
    mock_query_response.json.return_value = {
        "results": [
            {"id": "src1", "name": "Market Analysis", "type": "source"},
            {"id": "note1", "name": "Key Takeaway", "type": "note"}
        ]
    }

    # Mock Notes Creation Response
    mock_notes_response = MagicMock()
    mock_notes_response.status_code = 200
    mock_notes_response.json.return_value = {"id": "note2", "title": "New Finding"}

    mock_http_client = AsyncMock()

    with patch('tools.opennotebook_query.client.get_client', return_value=mock_http_client) as mock_q_client, \
         patch('tools.opennotebook_notes.client.get_client', return_value=mock_http_client) as mock_n_client:
        
        mock_q_client.get.return_value = mock_query_response
        mock_n_client.post.return_value = mock_notes_response

        # Step 1: Find items
        find_result = await query_tool.execute(
            notebook_id="nb123",
            name="Market Analysis"
        )
        assert "Market Analysis" in find_result.message or "results" in find_result.message.lower()

        # Step 2: Create a note based on findings (Simulated)
        create_result = await notes_tool.execute(
            notebook_id="nb123",
            title="Research Finding",
            content="Based on the query, I found this..."
        )
        assert "Finding" in create_result.message or "note2" in create_result.message


# --- Podcast Generation Workflow Integration Tests ---

@pytest.mark.asyncio
async def test_podcast_generation_flow(mock_agent):
    """Test the podcast flow: profiles -> generate -> status -> get."""
    # Setup Podcast Tool
    podcast_tool = OpenNotebookPodcasts()
    podcast_tool.agent = mock_agent

    # Mock Responses for different stages
    mock_profiles_response = MagicMock()
    mock_profiles_response.status_code = 200
    mock_profiles_response.json.return_value = {
        "episode_profiles": ["tech_discussion", "business_analysis"],
        "speaker_profiles": ["tech_experts", "solo_expert"]
    }

    mock_generate_response = MagicMock()
    mock_generate_response.status_code = 200
    mock_generate_response.json.return_value = {"job_id": "job_12345"}

    mock_status_response_running = MagicMock()
    mock_status_response_running.status_code = 200
    mock_status_response_running.json.return_value = {"status": "running", "message": "Generating..."}

    mock_status_response_complete = MagicMock()
    mock_status_response_complete.status_code = 200
    mock_status_response_complete.json.return_value = {
        "status": "completed", 
        "message": "Done", 
        "episode_id": "ep_67890"
    }

    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {
        "id": "ep_67890",
        "title": "Tech Talk",
        "audio_url": "http://localhost/audio.mp3",
        "transcript": "Hello and welcome..."
    }

    mock_http_client = AsyncMock()

    with patch('tools.opennotebook_podcasts.client.get_client', return_value=mock_http_client):
        # Step 1: Get Profiles
        podcast_tool.method = "profiles"
        profiles_result = await podcast_tool.execute()
        assert "tech_discussion" in profiles_result.message

        # Step 2: Generate Podcast
        podcast_tool.method = "generate"
        generate_result = await podcast_tool.execute(
            episode_profile="tech_discussion",
            speaker_profile="tech_experts",
            episode_name="My Podcast",
            notebook_id="nb123"
        )
        assert "job_12345" in generate_result.message or "job" in generate_result.message.lower()

        # Step 3: Check Status (Running)
        podcast_tool.method = "status"
        status_running = await podcast_tool.execute(job_id="job_12345")
        assert "running" in status_running.message.lower() or "generating" in status_running.message.lower()

        # Step 4: Check Status (Complete)
        mock_http_client.get.return_value = mock_status_response_complete
        status_complete = await podcast_tool.execute(job_id="job_12345")
        assert "completed" in status_complete.message.lower()

        # Step 5: Get Episode
        podcast_tool.method = "get"
        get_result = await podcast_tool.execute(episode_id="ep_67890")
        assert "Tech Talk" in get_result.message or "transcript" in get_result.message.lower()
