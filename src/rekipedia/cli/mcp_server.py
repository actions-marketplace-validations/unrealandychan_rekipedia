"""reki mcp — MCP stdio server exposing rekipedia graph as AI tools."""
from __future__ import annotations
import json
import sys
import os
from pathlib import Path

TOOLS = [
    {"name": "get_context", "description": "Get symbols and relationships for a file",
     "inputSchema": {"type": "object", "properties": {"file": {"type": "string"}}, "required": ["file"]}},
    {"name": "search_nodes", "description": "Search symbol names",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "get_relationships", "description": "Get callers and callees for a symbol",
     "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}},
    {"name": "get_knowledge_gaps", "description": "List untested high-call-count symbols",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_hub_nodes", "description": "List architectural chokepoints",
     "inputSchema": {"type": "object", "properties": {"top_n": {"type": "integer", "default": 10}}}},
    {"name": "get_impact", "description": "Blast-radius for a changed file",
     "inputSchema": {"type": "object", "properties": {"file": {"type": "string"}, "depth": {"type": "integer", "default": 2}}, "required": ["file"]}},
]

def _load_store(output_dir: str = "."):
    db_path = Path(output_dir) / ".rekipedia" / "rekipedia.db"
    if not db_path.exists():
        return None, None, None
    from rekipedia.storage.sqlite_store import SqliteStore
    store = SqliteStore(db_path)
    run_id = store.latest_run_id()
    if not run_id:
        return None, None, None
    symbols = store.get_all_symbols(run_id)
    rels = store.get_all_relationships(run_id)
    return store, symbols, rels

def _handle_tool(name: str, args: dict, symbols, rels) -> str:
    if symbols is None:
        return json.dumps({"error": "No rekipedia DB found. Run reki scan first."})
    
    if name == "get_context":
        file = args.get("file", "")
        syms = [s.name if hasattr(s, 'name') else s.get('name') for s in symbols
                if (s.file if hasattr(s, 'file') else s.get('file', '')) == file]
        file_rels = []
        for r in rels:
            frm = r.get('from_', '') or r.get('from', '') if isinstance(r, dict) else (r.from_ or '')
            if any(frm == s for s in syms):
                to = r.get('to', '') if isinstance(r, dict) else r.to
                kind = r.get('kind', '') if isinstance(r, dict) else r.kind
                file_rels.append({'from': frm, 'to': to, 'kind': kind})
        return json.dumps({'symbols': syms[:50], 'relationships': file_rels[:100]})
    
    elif name == "search_nodes":
        query = args.get("query", "").lower()
        matches = []
        for s in symbols:
            name_ = s.name if hasattr(s, 'name') else s.get('name', '')
            if query in name_.lower():
                matches.append({'name': name_, 'file': s.file if hasattr(s,'file') else s.get('file',''), 'kind': s.kind if hasattr(s,'kind') else s.get('kind','')})
        return json.dumps({'matches': matches[:50]})
    
    elif name == "get_relationships":
        symbol = args.get("symbol", "")
        callers, callees = [], []
        for r in rels:
            frm = r.get('from_', '') or r.get('from', '') if isinstance(r, dict) else (r.from_ or '')
            to = r.get('to', '') if isinstance(r, dict) else r.to
            kind = r.get('kind', '') if isinstance(r, dict) else r.kind
            if kind == 'calls':
                if to == symbol: callers.append(frm)
                if frm == symbol: callees.append(to)
        return json.dumps({'symbol': symbol, 'callers': callers[:30], 'callees': callees[:30]})
    
    elif name == "get_knowledge_gaps":
        from rekipedia.analysis.graph_analysis import _build_knowledge_gaps
        class FakeResult:
            pass
        r = FakeResult()
        r.symbols = symbols
        r.relationships = rels
        gaps = _build_knowledge_gaps(r)
        return json.dumps({'knowledge_gaps': gaps})
    
    elif name == "get_hub_nodes":
        from rekipedia.analysis.graph_analysis import _build_hub_nodes
        top_n = args.get('top_n', 10)
        hubs = _build_hub_nodes(rels, symbols, top_n=top_n)
        return json.dumps({'hub_nodes': hubs})
    
    elif name == "get_impact":
        from rekipedia.analysis.impact import compute_impact
        file = args.get('file', '')
        depth = args.get('depth', 2)
        result = compute_impact(file, rels, symbols, depth=depth)
        return json.dumps(result)
    
    return json.dumps({'error': f'Unknown tool: {name}'})


def run_mcp_server(output_dir: str = "."):
    """Run MCP JSON-RPC 2.0 stdio server."""
    _, symbols, rels = _load_store(output_dir)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        req_id = req.get('id')
        method = req.get('method', '')
        params = req.get('params', {})

        if method == 'initialize':
            resp = {'jsonrpc': '2.0', 'id': req_id, 'result': {
                'protocolVersion': '2024-11-05',
                'capabilities': {'tools': {}},
                'serverInfo': {'name': 'rekipedia', 'version': '1.0.0'},
            }}
        elif method == 'tools/list':
            resp = {'jsonrpc': '2.0', 'id': req_id, 'result': {'tools': TOOLS}}
        elif method == 'tools/call':
            tool_name = params.get('name', '')
            tool_args = params.get('arguments', {})
            result_text = _handle_tool(tool_name, tool_args, symbols, rels)
            resp = {'jsonrpc': '2.0', 'id': req_id, 'result': {
                'content': [{'type': 'text', 'text': result_text}]
            }}
        elif method == 'notifications/initialized':
            continue  # no response for notifications
        else:
            resp = {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': -32601, 'message': 'Method not found'}}
        
        print(json.dumps(resp), flush=True)
