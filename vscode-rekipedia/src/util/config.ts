import * as vscode from 'vscode';
import * as path from 'path';

export function getWikiDir(workspaceRoot: string): string {
  const cfg = vscode.workspace.getConfiguration('rekipedia');
  const rel = cfg.get<string>('wikiDir') ?? 'docs/wiki';
  return path.join(workspaceRoot, rel);
}
