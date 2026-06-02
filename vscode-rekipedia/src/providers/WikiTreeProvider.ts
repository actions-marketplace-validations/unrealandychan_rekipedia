import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { getWikiDir } from '../util/config';

export class WikiTreeProvider implements vscode.TreeDataProvider<WikiItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<WikiItem | undefined | null>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  constructor(private workspaceRoot: string) {}

  refresh(): void {
    this._onDidChangeTreeData.fire(null);
  }

  getTreeItem(element: WikiItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: WikiItem): WikiItem[] {
    const wikiDir = element?.resourceUri?.fsPath ?? getWikiDir(this.workspaceRoot);
    if (!fs.existsSync(wikiDir)) return [];
    return fs.readdirSync(wikiDir)
      .filter((f) => f.endsWith('.md') || fs.statSync(path.join(wikiDir, f)).isDirectory())
      .map((f) => {
        const full = path.join(wikiDir, f);
        const isDir = fs.statSync(full).isDirectory();
        return new WikiItem(
          f.replace(/\.md$/, ''),
          vscode.Uri.file(full),
          isDir ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None
        );
      });
  }
}

class WikiItem extends vscode.TreeItem {
  constructor(
    label: string,
    resourceUri: vscode.Uri,
    collapsibleState: vscode.TreeItemCollapsibleState
  ) {
    super(label, collapsibleState);
    this.resourceUri = resourceUri;
    if (collapsibleState === vscode.TreeItemCollapsibleState.None) {
      this.command = {
        command: 'markdown.showPreview',
        title: 'Open Preview',
        arguments: [resourceUri],
      };
      this.iconPath = new vscode.ThemeIcon('book');
    } else {
      this.iconPath = new vscode.ThemeIcon('folder');
    }
  }
}
