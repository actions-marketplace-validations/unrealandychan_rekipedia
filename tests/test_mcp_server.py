import json
from rekipedia.cli.mcp_server import TOOLS, _handle_tool

def test_tools_list():
    assert len(TOOLS) == 6
    names = {t['name'] for t in TOOLS}
    assert 'get_context' in names
    assert 'search_nodes' in names

def test_handle_tool_no_store():
    result = json.loads(_handle_tool('search_nodes', {'query': 'foo'}, None, None))
    assert 'error' in result

def test_search_nodes_empty():
    result = json.loads(_handle_tool('search_nodes', {'query': 'nonexistent_xyz'}, [], []))
    assert result['matches'] == []
