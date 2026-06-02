import * as vscode from 'vscode';
import { findReki } from './util/findReki';
import { runReki } from './reki';
import { AskPanel } from './providers/AskPanel';
import { SearchProvider } from './providers/SearchProvider';
import { WikiTreeProvider } from './providers/WikiTreeProvider';
import { RekiHoverProvider } from './providers/HoverProvider';

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  // Mark context active
  await vscode.commands.executeCommand('setContext', 'rekipedia.active', true);

  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath ?? '';

  // Wiki TreeView
  const wikiProvider = new WikiTreeProvider(workspaceRoot);
  context.subscriptions.push(
    vscode.window.createTreeView('rekipediaWiki', { treeDataProvider: wikiProvider, showCollapseAll: true })
  );

  // Hover provider — all languages
  context.subscriptions.push(
    vscode.languages.registerHoverProvider({ scheme: 'file' }, new RekiHoverProvider(workspaceRoot))
  );

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand('rekipedia.ask', () =>
      AskPanel.createOrShow(context.extensionUri, workspaceRoot)
    ),
    vscode.commands.registerCommand('rekipedia.search', () =>
      SearchProvider.showQuickPick(workspaceRoot)
    ),
    vscode.commands.registerCommand('rekipedia.refreshWiki', () => {
      wikiProvider.refresh();
    }),
    vscode.commands.registerCommand('rekipedia.scan', async () => {
      const reki = await findReki(workspaceRoot).catch((e: Error) => {
        vscode.window.showErrorMessage(e.message);
        return null;
      });
      if (!reki) return;

      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: 'Rekipedia: Scanning workspace…', cancellable: false },
        async () => {
          try {
            await runReki(reki, ['scan', '.'], workspaceRoot);
            wikiProvider.refresh();
            vscode.window.showInformationMessage('Rekipedia: Scan complete ✓');
          } catch (e) {
            vscode.window.showErrorMessage(`Rekipedia scan failed: ${e}`);
          }
        }
      );
    })
  );

  // Auto-scan on open if configured
  const cfg = vscode.workspace.getConfiguration('rekipedia');
  if (cfg.get<boolean>('autoScan') && workspaceRoot) {
    vscode.commands.executeCommand('rekipedia.scan');
  }
}

export function deactivate(): void {}
