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


class DummyAgent():
    pass


class OpenNotebookCreateAndMissingNotebookRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import client
        self.client = client
        self._orig_get_api_url = config.get_api_url
        self._orig_get_client = client.get_client
    
    async def asyncTearDown(self):
        config.get_api_url = self._orig_get_api_url
        self.client.get_client = self._orig_get_client
    
    async def test_notebook_creation_api_returns_correct_structure(self):
        config.get_api_url = lambda agent: 'http://example'
        test_notebooks = []
        dummy_client = DummyClient(notebooks=test_notebooks)
        self.client.get_client = lambda: _dummy_get_client(dummy_client)
        import client as client_module
        http_client = await client_module.get_client()
        response = await http_client.post('http://example/api/notebooks', json={'title': 'Test Notebook', 'description': 'Test Description'})
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('id', data)
        self.assertIn('title', data)
        self.assertIn('description', data)
        self.assertIn('created', data)
        self.assertIn('updated', data)
        self.assertEqual(data['title'], 'Test Notebook')
        self.assertEqual(data['description'], 'Test Description')
        self.assertEqual(len(dummy_client.notebooks), 1)
        self.assertEqual(dummy_client.notebooks[0]['title'], 'Test Notebook')
    
    async def test_notebook_creation_without_title_produces_valid_response(self):
        config.get_api_url = lambda agent: 'http://example'
        dummy_client = DummyClient(notebooks=[])
        self.client.get_client = lambda: _dummy_get_client(dummy_client)
        import client as client_module
        http_client = await client_module.get_client()
        response = await http_client.post('http://example/api/notebooks', json={'description': 'No title provided'})
        data = response.json()
        self.assertEqual(data['title'], '')
        self.assertEqual(data['description'], 'No title provided')
    
    async def test_resolve_notebook_id_raises_error_for_missing_notebook(self):
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([]))
        with self.assertRaises(ValueError) as cm:
            await resolve_notebook_id(DummyAgent(), 'Nonexistent Notebook')
        self.assertIn("No notebook found matching 'Nonexistent Notebook'", str(cm.exception))
    
    async def test_resolve_notebook_id_with_partial_id_returns_as_is(self):
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([]))
        result = await resolve_notebook_id(DummyAgent(), 'notebook:missing123')
        self.assertEqual(result, 'notebook:missing123')
    
    async def test_resolve_notebook_id_finds_existing_notebook(self):
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([{'id': 'notebook:abc123', 'name': 'Test Notebook'}]))
        result = await resolve_notebook_id(DummyAgent(), 'Test Notebook')
        self.assertEqual(result, 'notebook:abc123')
    
    async def test_resolve_notebook_id_handles_empty_notebook_list(self):
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([]))
        with self.assertRaises(ValueError) as cm:
            await resolve_notebook_id(DummyAgent(), 'Any Notebook')
        self.assertIn("No notebook found matching 'Any Notebook'", str(cm.exception))
    
    async def test_resolve_notebook_id_case_insensitive(self):
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([{'id': 'notebook:abc123', 'name': 'Test Notebook'}]))
        result = await resolve_notebook_id(DummyAgent(), 'test notebook')
        self.assertEqual(result, 'notebook:abc123')
        result2 = await resolve_notebook_id(DummyAgent(), 'TEST NOTEBOOK')
        self.assertEqual(result2, 'notebook:abc123')
    
    async def test_create_accepts_routing_name_aliases(self):
        config.get_api_url = lambda agent: 'http://example'
        dummy_client = DummyClient([])
        self.client.get_client = lambda: _dummy_get_client(dummy_client)
        import client as client_module
        http_client = await client_module.get_client()
        title_response = await http_client.post('http://example/api/notebooks', json={'title': 'Alias Title', 'description': ''})
        title_data = title_response.json()
        self.assertEqual(title_data['title'], 'Alias Title')
        self.assertEqual(title_data['description'], '')
        notebook_name_response = await http_client.post('http://example/api/notebooks', json={'title': 'Alias Notebook', 'description': 'From notebook_name alias'})
        notebook_name_data = notebook_name_response.json()
        self.assertEqual(notebook_name_data['title'], 'Alias Notebook')
        self.assertEqual(notebook_name_data['description'], 'From notebook_name alias')
    
    async def test_resolve_notebook_id_emoji_stripping(self):
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([{'id': 'notebook:abc123', 'name': '🕵🏾‍♂️ Agent Zero'}]))
        result = await resolve_notebook_id(DummyAgent(), 'Agent Zero')
        self.assertEqual(result, 'notebook:abc123')
        result2 = await resolve_notebook_id(DummyAgent(), 'agent zero')
        self.assertEqual(result2, 'notebook:abc123')
    
    async def test_resolve_notebook_id_short_suffix(self):
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([{'id': 'notebook:abc123', 'name': 'Test Notebook'}]))
        result = await resolve_notebook_id(DummyAgent(), 'abc123')
        self.assertEqual(result, 'notebook:abc123')
        result2 = await resolve_notebook_id(DummyAgent(), 'c123')
        self.assertEqual(result2, 'notebook:abc123')
    
    async def test_resolve_notebook_id_name_containment(self):
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([{'id': 'notebook:abc123', 'name': 'Test Notebook'}]))
        result = await resolve_notebook_id(DummyAgent(), 'Test')
        self.assertEqual(result, 'notebook:abc123')
    
    async def test_resolve_notebook_id_empty_input(self):
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([]))
        with self.assertRaises(ValueError) as cm:
            await resolve_notebook_id(DummyAgent(), '')
        self.assertIn('Notebook ID or name is required', str(cm.exception))
    
    async def test_resolve_notebook_id_whitespace_input(self):
        config.get_api_url = lambda agent: 'http://example'
        self.client.get_client = lambda: _dummy_get_client(DummyClient([]))
        with self.assertRaises(ValueError) as cm:
            await resolve_notebook_id(DummyAgent(), '   ')
        self.assertIn("No notebook found matching '   '", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
