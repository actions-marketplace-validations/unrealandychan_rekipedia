"""Graph export to GraphML, Neo4j Cypher, Obsidian wikilinks."""
from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET


def export_graphml(symbols: list, relationships: list) -> str:
    """Export graph as GraphML XML string."""
    root = ET.Element('graphml', xmlns='http://graphml.graphdrawing.org/graphml')
    for attr, typ in [('kind', 'string'), ('file', 'string')]:
        ET.SubElement(root, 'key', id=f'k_{attr}', **{'for': 'node', 'attr.name': attr, 'attr.type': typ})
    ET.SubElement(root, 'key', id='k_kind_e', **{'for': 'edge', 'attr.name': 'kind', 'attr.type': 'string'})

    graph = ET.SubElement(root, 'graph', id='G', edgedefault='directed')

    for s in symbols:
        name = s.name if hasattr(s, 'name') else s.get('name', '')
        file = s.file if hasattr(s, 'file') else s.get('file', '')
        kind = s.kind if hasattr(s, 'kind') else s.get('kind', '')
        if not name:
            continue
        node = ET.SubElement(graph, 'node', id=name)
        d1 = ET.SubElement(node, 'data', key='k_kind'); d1.text = kind
        d2 = ET.SubElement(node, 'data', key='k_file'); d2.text = file

    for i, r in enumerate(relationships):
        frm = r.get('from_', '') or r.get('from', '') if isinstance(r, dict) else (r.from_ or '')
        to = r.get('to', '') if isinstance(r, dict) else r.to
        kind = r.get('kind', '') if isinstance(r, dict) else r.kind
        if not frm or not to:
            continue
        edge = ET.SubElement(graph, 'edge', id=f'e{i}', source=frm, target=to)
        d = ET.SubElement(edge, 'data', key='k_kind_e'); d.text = kind

    return ET.tostring(root, encoding='unicode', xml_declaration=False)


def export_cypher(symbols: list, relationships: list) -> str:
    """Export graph as Neo4j Cypher CREATE statements."""
    lines = ['// rekipedia graph export — Neo4j Cypher']
    for s in symbols:
        name = s.name if hasattr(s, 'name') else s.get('name', '')
        kind = s.kind if hasattr(s, 'kind') else s.get('kind', '')
        file = s.file if hasattr(s, 'file') else s.get('file', '')
        if not name:
            continue
        safe = name.replace("'", "\\'")
        safe_file = file.replace("'", "\\'")
        lines.append(f"CREATE (:`Symbol` {{name: '{safe}', kind: '{kind}', file: '{safe_file}'}})")
    lines.append('')
    for r in relationships:
        frm = r.get('from_', '') or r.get('from', '') if isinstance(r, dict) else (r.from_ or '')
        to = r.get('to', '') if isinstance(r, dict) else r.to
        kind = (r.get('kind', '') if isinstance(r, dict) else r.kind).upper().replace('-', '_')
        if not frm or not to:
            continue
        sf = frm.replace("'", "\\'")
        st = to.replace("'", "\\'")
        lines.append(f"MATCH (a:Symbol {{name: '{sf}'}}), (b:Symbol {{name: '{st}'}}) CREATE (a)-[:{kind}]->(b);")
    return '\n'.join(lines)


def export_obsidian(symbols: list, relationships: list, output_dir: Path) -> list[Path]:
    """Write one .md file per symbol with wikilinks to callees."""
    output_dir.mkdir(parents=True, exist_ok=True)

    callees: dict[str, list[str]] = {}
    for r in relationships:
        frm = r.get('from_', '') or r.get('from', '') if isinstance(r, dict) else (r.from_ or '')
        to = r.get('to', '') if isinstance(r, dict) else r.to
        kind = r.get('kind', '') if isinstance(r, dict) else r.kind
        if frm and to and kind in ('calls', 'imports', 'inherits'):
            callees.setdefault(frm, []).append(to)

    written = []
    for s in symbols:
        name = s.name if hasattr(s, 'name') else s.get('name', '')
        kind = s.kind if hasattr(s, 'kind') else s.get('kind', '')
        file = s.file if hasattr(s, 'file') else s.get('file', '')
        if not name:
            continue
        safe_name = name.replace('/', '_').replace(':', '_')
        md_path = output_dir / f'{safe_name}.md'
        links = callees.get(name, [])
        lines = [f'# {name}', '', f'**Kind:** {kind}  ', f'**File:** `{file}`', '']
        if links:
            lines.append('## References')
            for link in links[:20]:
                lines.append(f'- [[{link}]]')
        md_path.write_text('\n'.join(lines), encoding='utf-8')
        written.append(md_path)
    return written
