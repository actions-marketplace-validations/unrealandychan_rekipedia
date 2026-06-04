import * as vscode from 'vscode';
import { findReki } from '../util/findReki';
import { runReki } from '../reki';

interface SearchResult {
  name: string;
  file: string;
  line: number;
  kind: string;
  summary?: string;
}

export class SearchProvider {
  public static async showQuickPick(workspaceRoot: string): Promise<void> {
    let reki: string;
    try {
      reki = await findReki(workspaceRoot);
    } catch (e) {
      vscode.window.showErrorMessage(String(e));
      return;
    }

    const qp = vscode.window.createQuickPick();
    qp.placeholder = 'Search rekipedia symbols…';
    qp.matchOnDescription = true;
    qp.matchOnDetail = true;

    let debounce: NodeJS.Timeout | undefined;

    qp.onDidChangeValue((query) => {
      if (debounce) clearTimeout(debounce);
      if (!query.trim()) { qp.items = []; return; }
      debounce = setTimeout(async () => {
        qp.busy = true;
        try {
          const raw = await runReki(reki, ['search', query, '--json'], workspaceRoot);
          const results: SearchResult[] = JSON.parse(raw);
          qp.items = results.map((r) => ({
            label: r.name,
            description: r.kind,
            detail: `${r.file}:${r.line}${r.summary ? '  ' + r.summary : ''}`,
            _file: r.file,
            _line: r.line,
          } as vscode.QuickPickItem & { _file: string; _line: number }));
        } catch {
          qp.items = [{ label: '$(error) Search failed', description: 'Check reki is installed' }];
        } finally {
          qp.busy = false;
        }
      }, 200);
    });

    qp.onDidAccept(async () => {
      const sel = qp.selectedItems[0] as vscode.QuickPickItem & { _file?: string; _line?: number };
      if (!sel?._file) return;
      qp.hide();
      const absPath = sel._file.startsWith('/') ? sel._file : `${workspaceRoot}/${sel._file}`;
      const doc = await vscode.workspace.openTextDocument(absPath);
      const editor = await vscode.window.showTextDocument(doc);
      const line = (sel._line ?? 1) - 1;
      const range = new vscode.Range(line, 0, line, 0);
      editor.selection = new vscode.Selection(range.start, range.end);
      editor.revealRange(range, vscode.TextEditorRevealType.InCenter);
    });

    qp.show();
  }
}
