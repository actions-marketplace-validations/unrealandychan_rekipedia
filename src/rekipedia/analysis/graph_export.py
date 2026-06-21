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


def export_obsidian(
    symbols: list,
    relationships: list,
    output_dir: Path,
    wiki_dir: Path | None = None,
    diagrams_dir: Path | None = None,
) -> list[Path]:
    """Write one .md file per symbol with wikilinks, and copy/convert wiki pages & diagrams."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    import re

    # 1. Build Inbound and Outbound relationships
    callees: dict[str, list[tuple[str, str]]] = {}  # frm -> [(to, kind)]
    callers: dict[str, list[tuple[str, str]]] = {}  # to -> [(frm, kind)]

    for r in relationships:
        frm = r.get('from_', '') or r.get('from', '') if isinstance(r, dict) else getattr(r, 'from_', '') or getattr(r, 'from', '')
        to = r.get('to', '') if isinstance(r, dict) else getattr(r, 'to', '')
        kind = r.get('kind', '') if isinstance(r, dict) else getattr(r, 'kind', '')
        if frm and to and kind in ('calls', 'imports', 'inherits'):
            callees.setdefault(frm, []).append((to, kind))
            callers.setdefault(to, []).append((frm, kind))

    # Determine symbol target directory
    # If wiki_dir is provided, we organize symbols under a "symbols" folder to keep root clean
    sym_dir = output_dir / "symbols" if wiki_dir else output_dir
    if wiki_dir:
        sym_dir.mkdir(parents=True, exist_ok=True)

    # 2. Write Symbol Notes
    for s in symbols:
        name = s.name if hasattr(s, 'name') else s.get('name', '')
        kind = s.kind if hasattr(s, 'kind') else s.get('kind', '')
        file = s.file if hasattr(s, 'file') else s.get('file', '')
        if not name:
            continue
        safe_name = name.replace('/', '_').replace(':', '_')
        md_path = sym_dir / f'{safe_name}.md'

        # Fetch relations
        out_rels = callees.get(name, [])
        in_rels = callers.get(name, [])

        # Build card content with frontmatter
        lines = [
            '---',
            f'kind: {kind}',
            f'file: {file}',
            'tags:',
            '  - codebase/symbol',
            f'  - codebase/{kind}',
            '---',
            '',
            f'# {name}',
            '',
            f'**Kind:** {kind}  ',
            f'**File:** `{file}`',
            '',
        ]

        if out_rels or in_rels:
            lines.append('## References')
            
            if out_rels:
                lines.append('### Outgoing')
                for target, rel_kind in out_rels[:50]:  # Up to 50
                    safe_target = target.replace('/', '_').replace(':', '_')
                    lines.append(f'- [[{safe_target}]] ({rel_kind})')
                lines.append('')
                
            if in_rels:
                lines.append('### Incoming')
                for source, rel_kind in in_rels[:50]:  # Up to 50
                    safe_source = source.replace('/', '_').replace(':', '_')
                    lines.append(f'- [[{safe_source}]] (called by {rel_kind})')
                lines.append('')

        md_path.write_text('\n'.join(lines), encoding='utf-8')
        written.append(md_path)

    # 3. Helper function for link conversion
    def convert_md_links_to_wikilinks(text: str) -> str:
        # Converts [Display](file.md#anchor) -> [[file#anchor|Display]]
        pattern = r'\[([^\]]+)\]\(([^)]+?)\.md(#?[^)]*)\)'
        def replace(match):
            display = match.group(1)
            path_part = match.group(2)
            anchor = match.group(3)
            stem = Path(path_part).name
            if anchor:
                return f"[[{stem}{anchor}|{display}]]"
            return f"[[{stem}|{display}]]"
        return re.sub(pattern, replace, text)

    # 4. Copy and Convert Wiki Pages
    if wiki_dir and wiki_dir.exists():
        for p in sorted(wiki_dir.glob("*.md")):
            content = p.read_text(encoding="utf-8")
            converted_content = convert_md_links_to_wikilinks(content)
            
            # Put wiki pages at the root of the output directory
            dest_path = output_dir / p.name
            dest_path.write_text(converted_content, encoding="utf-8")
            written.append(dest_path)

    # 5. Copy and Convert Diagrams
    if diagrams_dir and diagrams_dir.exists():
        diag_out = output_dir / "diagrams"
        diag_out.mkdir(parents=True, exist_ok=True)
        for p in sorted(diagrams_dir.glob("*.md")):
            content = p.read_text(encoding="utf-8")
            converted_content = convert_md_links_to_wikilinks(content)
            
            dest_path = diag_out / p.name
            dest_path.write_text(converted_content, encoding="utf-8")
            written.append(dest_path)

    return written
