import * as fs from 'fs';
import * as path from 'path';
import { which } from './which';
import * as vscode from 'vscode';

export async function findReki(workspaceRoot: string): Promise<string> {
  // 1. Workspace setting
  const cfg = vscode.workspace.getConfiguration('rekipedia');
  const settingPath = cfg.get<string>('rekiPath')?.trim();
  if (settingPath && fs.existsSync(settingPath)) {
    return settingPath;
  }

  // 2. Active venv
  const venvCandidates = [
    path.join(workspaceRoot, 'venv', 'bin', 'reki'),
    path.join(workspaceRoot, '.venv', 'bin', 'reki'),
  ];
  for (const p of venvCandidates) {
    if (fs.existsSync(p)) return p;
  }

  // 3. PATH
  const inPath = await which('reki');
  if (inPath) return inPath;

  throw new Error(
    'reki binary not found. Install rekipedia: pip install rekipedia  ' +
    'or set rekipedia.rekiPath in workspace settings.'
  );
}
