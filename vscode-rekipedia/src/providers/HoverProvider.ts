import * as vscode from 'vscode';
import { findReki } from '../util/findReki';
import { runReki } from '../reki';

export class RekiHoverProvider implements vscode.HoverProvider {
  constructor(private workspaceRoot: string) {}

  async provideHover(document: vscode.TextDocument, position: vscode.Position): Promise<vscode.Hover | null> {
    const wordRange = document.getWordRangeAtPosition(position);
    if (!wordRange) return null;
    const word = document.getText(wordRange);
    if (word.length < 3) return null;

    let reki: string;
    try {
      reki = await findReki(this.workspaceRoot);
    } catch {
      return null;
    }

    try {
      const raw = await runReki(reki, ['search', word, '--json', '--limit', '1'], this.workspaceRoot);
      const results = JSON.parse(raw);
      if (!results?.length) return null;
      const r = results[0];
      const md = new vscode.MarkdownString();
      md.isTrusted = true;
      md.appendMarkdown(`**${r.name}** \`${r.kind}\`\n\n`);
      if (r.summary) md.appendMarkdown(r.summary + '\n\n');
      md.appendMarkdown(`[$(go-to-file) ${r.file}:${r.line}](command:rekipedia.search)`);
      return new vscode.Hover(md, wordRange);
    } catch {
      return null;
    }
  }
}
