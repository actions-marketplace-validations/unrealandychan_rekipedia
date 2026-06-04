import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { findReki } from '../util/findReki';
import { streamReki } from '../reki';

export class AskPanel {
  public static currentPanel: AskPanel | undefined;
  private readonly _panel: vscode.WebviewPanel;
  private readonly _workspaceRoot: string;
  private _disposables: vscode.Disposable[] = [];

  public static createOrShow(extensionUri: vscode.Uri, workspaceRoot: string): void {
    const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
    if (AskPanel.currentPanel) {
      AskPanel.currentPanel._panel.reveal(column);
      return;
    }
    const panel = vscode.window.createWebviewPanel(
      'rekipediaAsk', 'Rekipedia: Ask',
      column,
      { enableScripts: true, retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] }
    );
    AskPanel.currentPanel = new AskPanel(panel, workspaceRoot);
  }

  private constructor(panel: vscode.WebviewPanel, workspaceRoot: string) {
    this._panel = panel;
    this._workspaceRoot = workspaceRoot;
    this._panel.webview.html = this._getHtml();
    this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    this._panel.webview.onDidReceiveMessage(async (msg) => {
      if (msg.type === 'ask') await this._handleAsk(msg.query);
    }, null, this._disposables);
  }

  private async _handleAsk(query: string): Promise<void> {
    const post = (data: object) => this._panel.webview.postMessage(data);
    post({ type: 'start', query });
    try {
      const reki = await findReki(this._workspaceRoot);
      await streamReki(reki, ['ask', query, '--json'], this._workspaceRoot, (line) => {
        if (line.startsWith('__error__:')) {
          post({ type: 'error', text: line.slice(10) });
        } else {
          try {
            const chunk = JSON.parse(line);
            post({ type: 'chunk', ...chunk });
          } catch {
            post({ type: 'text', text: line });
          }
        }
      });
      post({ type: 'done' });
    } catch (e) {
      post({ type: 'error', text: String(e) });
    }
  }

  private _getHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Rekipedia Ask</title>
<style>
  body { font-family: var(--vscode-font-family); background: var(--vscode-editor-background); color: var(--vscode-editor-foreground); margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; }
  #messages { flex: 1; overflow-y: auto; padding: 12px 16px; display: flex; flex-direction: column; gap: 12px; }
  .msg { padding: 8px 12px; border-radius: 6px; white-space: pre-wrap; line-height: 1.5; }
  .msg.user { background: var(--vscode-button-background); color: var(--vscode-button-foreground); align-self: flex-end; max-width: 80%; }
  .msg.assistant { background: var(--vscode-editor-inactiveSelectionBackground); align-self: flex-start; max-width: 90%; }
  .msg.error { background: var(--vscode-inputValidation-errorBackground); color: var(--vscode-inputValidation-errorForeground); }
  .citation { color: var(--vscode-textLink-foreground); cursor: pointer; text-decoration: underline; }
  #input-area { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--vscode-panel-border); }
  #query { flex: 1; padding: 8px; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); border-radius: 4px; font-size: 13px; }
  #send { padding: 8px 16px; background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; border-radius: 4px; cursor: pointer; }
  #send:hover { background: var(--vscode-button-hoverBackground); }
  .thinking { opacity: 0.6; font-style: italic; }
</style>
</head>
<body>
<div id="messages"><div class="msg assistant">👋 Ask anything about this codebase. I'll answer with file:line citations.</div></div>
<div id="input-area">
  <input id="query" type="text" placeholder="How does authentication work?" />
  <button id="send">Ask</button>
</div>
<script>
  const vscode = acquireVsCodeApi();
  const messages = document.getElementById('messages');
  const queryInput = document.getElementById('query');
  const sendBtn = document.getElementById('send');

  let currentBubble = null;

  function addMessage(cls, text) {
    const div = document.createElement('div');
    div.className = 'msg ' + cls;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function send() {
    const q = queryInput.value.trim();
    if (!q) return;
    queryInput.value = '';
    addMessage('user', q);
    currentBubble = addMessage('assistant thinking', '...');
    sendBtn.disabled = true;
    vscode.postMessage({ type: 'ask', query: q });
  }

  sendBtn.addEventListener('click', send);
  queryInput.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });

  window.addEventListener('message', e => {
    const msg = e.data;
    if (msg.type === 'start') {
      currentBubble.textContent = '';
      currentBubble.classList.remove('thinking');
    } else if (msg.type === 'chunk' || msg.type === 'text') {
      const text = msg.text || msg.answer || '';
      currentBubble.textContent += text;
      // render citations
      if (msg.citations) {
        msg.citations.forEach(c => {
          const span = document.createElement('span');
          span.className = 'citation';
          span.textContent = ' [' + c.file + ':' + c.line + ']';
          span.dataset.file = c.file;
          span.dataset.line = c.line;
          currentBubble.appendChild(span);
        });
      }
      messages.scrollTop = messages.scrollHeight;
    } else if (msg.type === 'done') {
      sendBtn.disabled = false;
    } else if (msg.type === 'error') {
      if (currentBubble) currentBubble.remove();
      addMessage('error', '⚠ ' + msg.text);
      sendBtn.disabled = false;
    }
  });

  // Citation click -> open file
  messages.addEventListener('click', e => {
    const target = e.target;
    if (target.classList.contains('citation')) {
      vscode.postMessage({ type: 'openFile', file: target.dataset.file, line: parseInt(target.dataset.line) });
    }
  });
</script>
</body>
</html>`;
  }

  public dispose(): void {
    AskPanel.currentPanel = undefined;
    this._panel.dispose();
    this._disposables.forEach(d => d.dispose());
  }
}
