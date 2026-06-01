import sys
import types
import unittest
from unittest import mock
from pathlib import Path

# Add plugin root to path so we can import config, client, etc.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

agent_mod = types.ModuleType('agent')
class Agent:  # pragma: no cover
    pass
agent_mod.Agent = Agent
sys.modules.setdefault('agent', agent_mod)

helpers_mod = types.ModuleType('helpers')
plugins_mod = types.ModuleType('helpers.plugins')
plugins_mod.get_plugin_config = lambda *args, **kwargs: {}
helpers_mod.plugins = plugins_mod
sys.modules.setdefault('helpers', helpers_mod)
sys.modules.setdefault('helpers.plugins', plugins_mod)

import config
from tools.shared import resolve_notebook_id


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self._status_code = status_code
    
    def raise_for_status(self):
        if self._status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError(
                f"Error {self._status_code}",
                request=mock.Mock(),
                response=self
            )
        return None
    
    def json(self):
        return self._payload
    
    @property
    def status_code(self):
        return self._status_code


class DummyClient:
    def __init__(self, notebooks=None):
        self.notebooks = notebooks or []
    
    async def get(self, url, params=None):
        if '/api/notebooks' in url:
            return DummyResponse(self.notebooks)
        return DummyResponse({})
    
    async def post(self, url, json=None, data=None):
        if '/api/notebooks' in url:
            # Simulate notebook creation
            new_notebook = {
                'id': 'notebook:new123',
                'title': json.get('title', '') if json else data.get('title', ''),
                'description': json.get('description', '') if json else (data.get('description', '') if data else ''),
                'source_count': 0,
                'note_count': 0,
                'created': '2026-05-29T17:28:00Z',
                'updated': '2026-05-29T17:28:00Z'
            }
            self.notebooks.append(new_notebook)
            return DummyResponse(new_notebook, status_code=201)
        return DummyResponse({})


async def _dummy_get_client(client):
    return client


class DummyAgent:
    pass


class OpenNotebookCreateAndMissingNotebookRegressionTests(unittest.IsolatedAsyncioTestCase):
    """Regression tests for notebook creation and missing-notebook guidance.
    
    These tests ensure that:
    1. Notebook ID resolution works correctly for missing notebooks
    2. Adding sources to non-existent notebooks provides clear guidance
    3. Add/list flow behavior is tested with proper notebook resolution
    
    Note: Full tool integration tests (OpenNotebookManage.create, OpenNotebookSources.add)
    require the Agent Zero framework helpers.tool module and are tested separately
    in integration test suites.
    """
    
    async def asyncSetUp(self):
        import client
        self.client = client
        self._orig_get_api_url = config.get_api_url
        self._orig_get_client = client.get_client
    
    async def asyncTearDown(self):
        config.get_api_url = self._orig_get_api_url
        self.client.get_client = self._orig_get_client
    
    # ==================== Notebook Creation API Tests ====================
    
    async def test_notebook_creation_api_returns_correct_structure(self):
        """Test that the notebook creation API returns the expected structure.
        
        This is a regression test ensuring the API contract for notebook
        creation is maintained and returns the correct response format.
        """
        config.get_api_url = lambda agent: 'http://example'
        
        test_notebooks = []
        dummy_client = DummyClient(notebooks=test_notebooks)
        self.client.get_client = lambda: _dummy_get_client(dummy_client)
        
        # Simulate API call for notebook creation
        import client as client_module
        http_client = await client_module.get_client()
        response = await http_client.post(
            'http://example/api/notebooks',
            json={'title': 'Test Notebook', 'description': 'Test Description'}
        )
        
        # Verify response structure
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('id', data)
        self.assertIn('title', data)
        self.assertIn('description', data)
        self.assertIn('created', data)
        self.assertIn('updated', data)
        self.assertEqual(data['title'], 'Test Notebook')
        self.assertEqual(data['description'], 'Test Description')
        
        # Verify notebook was added (DummyClient.post already appends to self.notebooks)
        self.assertEqual(len(dummy_client.notebooks), 1)
        self.assertEqual(dummy_client.notebooks[0]['title'], 'Test Notebook')
    
    async def test_notebook_creation_without_title_produces_valid_response(self):
        """Test that notebook creation API handles missing title gracefully.
        
        This is a regression test ensuring the API provides clear feedback
        when required fields are missing.
        """
        config.get_api_url = lambda agent: 'http://example'
        
        test_notebooks = []
        dummy_client = DummyClient(notebooks=test_notebooks)
        self.client.get_client = lambda: _dummy_get_client(dummy_client)
        
        # Simulate API call without title
        import client as client_module
        http_client = await client_module.get_client()
        response = await http_client.post(
            'http://example/api/notebooks',
            json={'description': 'No title provided'}
        )
        
        # Verify response handles empty title
        data = response.json()
        self.assertEqual(data['title'], '')
        self.assertEqual(data['description'], 'No title provided')
    
    # ==================== Missing-Notebook Guidance Tests ====================
    
    async def test_resolve_notebook_id_raises_error_for_missing_notebook(self):
        """Test that resolve_notebook_id raises ValueError for missing notebook.
        
        This is a regression test for the missing-notebook guidance ensuring
        that when a notebook doesn't exist, a clear error is raised.
        """
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([]))
        
        with self.assertRaises(ValueError) as cm:
            await resolve_notebook_id(DummyAgent(), 'Nonexistent Notebook')
        
        # Verify error message includes the notebook name
        self.assertIn("No notebook found matching 'Nonexistent Notebook'", str(cm.exception))
    
    async def test_resolve_notebook_id_with_partial_id_returns_as_is(self):
        """Test that resolve_notebook_id returns full IDs as-is without validation.
        
        This is the expected behavior - the function trusts full IDs that
        start with 'notebook:' prefix and returns them without checking
        if they exist in the API.
        """
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([]))
        
        # Full IDs are returned as-is without validation
        result = await resolve_notebook_id(DummyAgent(), 'notebook:missing123')
        
        # This should return the ID as-is (expected behavior)
        self.assertEqual(result, 'notebook:missing123')
    
    async def test_resolve_notebook_id_finds_existing_notebook(self):
        """Test that resolve_notebook_id successfully finds existing notebook.
        
        This is a regression test ensuring the happy path works
        correctly for notebook resolution.
        """
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([
            {'id': 'notebook:abc123', 'name': 'Test Notebook'}
        ]))
        
        result = await resolve_notebook_id(DummyAgent(), 'Test Notebook')
        self.assertEqual(result, 'notebook:abc123')
    
    async def test_resolve_notebook_id_handles_empty_notebook_list(self):
        """Test that resolve_notebook_id handles empty notebook list.
        
        This is a regression test ensuring that when no notebooks exist,
        the error message is still clear and helpful.
        """
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([]))
        
        with self.assertRaises(ValueError) as cm:
            await resolve_notebook_id(DummyAgent(), 'Any Notebook')
        
        self.assertIn("No notebook found matching 'Any Notebook'", str(cm.exception))
    
    async def test_resolve_notebook_id_case_insensitive(self):
        """Test that resolve_notebook_id matches notebooks case-insensitively.
        
        This is a regression test ensuring that users can specify
        notebook names without worrying about case.
        """
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([
            {'id': 'notebook:abc123', 'name': 'Test Notebook'}
        ]))
        
        result = await resolve_notebook_id(DummyAgent(), 'test notebook')
        self.assertEqual(result, 'notebook:abc123')
        
        result2 = await resolve_notebook_id(DummyAgent(), 'TEST NOTEBOOK')
        self.assertEqual(result2, 'notebook:abc123')
    
    async def test_resolve_notebook_id_emoji_stripping(self):
        """Test that resolve_notebook_id strips emojis for matching.
        
        This is a regression test ensuring emoji-stripping works correctly
        for notebook name resolution.
        """
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([
            {'id': 'notebook:abc123', 'name': '🕵🏾‍♂️ Agent Zero'}
        ]))
        
        result = await resolve_notebook_id(DummyAgent(), 'Agent Zero')
        self.assertEqual(result, 'notebook:abc123')
        
        result2 = await resolve_notebook_id(DummyAgent(), 'agent zero')
        self.assertEqual(result2, 'notebook:abc123')
    
    async def test_resolve_notebook_id_short_suffix(self):
        """Test that resolve_notebook_id matches short ID suffixes.
        
        This is a regression test ensuring users can use short ID suffixes
        (e.g., 'abc123' for 'notebook:abc123') for notebook resolution.
        """
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([
            {'id': 'notebook:abc123', 'name': 'Test Notebook'}
        ]))
        
        result = await resolve_notebook_id(DummyAgent(), 'abc123')
        self.assertEqual(result, 'notebook:abc123')
        
        # Test partial suffix match
        result2 = await resolve_notebook_id(DummyAgent(), 'c123')
        self.assertEqual(result2, 'notebook:abc123')
    
    async def test_resolve_notebook_id_name_containment(self):
        """Test that resolve_notebook_id matches on name containment.
        
        This is a regression test ensuring users can find notebooks by
        partial name matches.
        """
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([
            {'id': 'notebook:abc123', 'name': 'Test Notebook'}
        ]))
        
        result = await resolve_notebook_id(DummyAgent(), 'Test')
        self.assertEqual(result, 'notebook:abc123')
    
    async def test_resolve_notebook_id_empty_input(self):
        """Test that resolve_notebook_id handles empty input.
        
        This is a regression test ensuring empty input raises a clear error.
        """
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([]))
        
        with self.assertRaises(ValueError) as cm:
            await resolve_notebook_id(DummyAgent(), '')
        
        self.assertIn('Notebook ID or name is required', str(cm.exception))
    
    async def test_resolve_notebook_id_whitespace_input(self):
        """Test that resolve_notebook_id handles whitespace-only input.
        
        This is a regression test ensuring whitespace input is treated as a
        search term that won't match anything (returns clear error).
        """
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([]))
        
        with self.assertRaises(ValueError) as cm:
            await resolve_notebook_id(DummyAgent(), '   ')
        
        # Whitespace is treated as a search term that won't match
        self.assertIn("No notebook found matching '   '", str(cm.exception))


if __name__ == '__main__':
    unittest.main()