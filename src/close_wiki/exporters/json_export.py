"""Export knowledge as JSON files + manifest.json."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from close_wiki.models.contracts import AnalysisResult, FileManifest


class JsonExporter:
    def __init__(self, output_dir: Path) -> None:
        self._exports_dir = output_dir / "exports"

    def export(
        self,
        run_id: str,
        files: list[FileManifest],
        combined: AnalysisResult,
        pages: dict[str, tuple[str, str]],
        diagrams: dict[str, tuple[str, str]],
    ) -> None:
        self._exports_dir.mkdir(parents=True, exist_ok=True)

        # symbols.json
        symbols_path = self._exports_dir / "symbols.json"
        symbols_path.write_text(
            json.dumps(
                [s.model_dump() for s in combined.symbols],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        # relationships.json
        rels_path = self._exports_dir / "relationships.json"
        rels_path.write_text(
            json.dumps(
                [r.model_dump(by_alias=True) for r in combined.relationships],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        # manifest.json
        manifest = {
            "run_id": run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "file_count": len(files),
            "symbol_count": len(combined.symbols),
            "relationship_count": len(combined.relationships),
            "pages": [
                {"slug": slug, "title": title}
                for slug, (title, _) in pages.items()
            ],
            "diagrams": list(diagrams.keys()),
            "risks": combined.risks,
            "build_commands": combined.build_commands,
            "test_commands": combined.test_commands,
        }
        manifest_path = self._exports_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
