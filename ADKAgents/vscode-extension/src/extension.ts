import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as https from 'https';
import * as http from 'http';

export function activate(context: vscode.ExtensionContext) {
    const cmd = vscode.commands.registerCommand('automationGenerator.open', () => {
        AutomationPanel.createOrShow(context);
    });
    context.subscriptions.push(cmd);

    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.text = '$(beaker) Auto Framework';
    statusBar.tooltip = 'Generate Automation Framework';
    statusBar.command = 'automationGenerator.open';
    statusBar.show();
    context.subscriptions.push(statusBar);
}

export function deactivate() {}

interface GeneratedFile {
    filename: string;
    content: string;
}

class AutomationPanel {
    static currentPanel?: AutomationPanel;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _context: vscode.ExtensionContext;
    private readonly _disposables: vscode.Disposable[] = [];

    static createOrShow(context: vscode.ExtensionContext) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (AutomationPanel.currentPanel) {
            AutomationPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            'automationGenerator',
            'Automation Framework Generator',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'media')],
            }
        );
        AutomationPanel.currentPanel = new AutomationPanel(panel, context);
    }

    private constructor(panel: vscode.WebviewPanel, context: vscode.ExtensionContext) {
        this._panel = panel;
        this._context = context;
        this._render();
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.type) {
                case 'generate': await this._generate(msg.payload); break;
                case 'write':    await this._writeFiles(msg.files as GeneratedFile[]); break;
                case 'copy':     await vscode.env.clipboard.writeText(msg.text); break;
            }
        }, null, this._disposables);
    }

    private async _generate(payload: Record<string, unknown>) {
        const config = vscode.workspace.getConfiguration('automationGenerator');
        const apiUrl = config.get<string>('apiUrl') || 'https://agent-service-eguulmisoa-uc.a.run.app';
        try {
            const data = await this._post(`${apiUrl}/api/generate-framework`, payload);
            this._panel.webview.postMessage({ type: 'files', data });
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : String(err);
            this._panel.webview.postMessage({ type: 'error', message: msg });
        }
    }

    private _post(url: string, body: unknown): Promise<unknown> {
        return new Promise((resolve, reject) => {
            const raw = JSON.stringify(body);
            const parsed = new URL(url);
            const lib = parsed.protocol === 'https:' ? https : http;
            const req = lib.request(
                {
                    hostname: parsed.hostname,
                    port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
                    path: parsed.pathname,
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(raw) },
                },
                (res) => {
                    let data = '';
                    res.on('data', (chunk: string) => (data += chunk));
                    res.on('end', () => {
                        try { resolve(JSON.parse(data)); }
                        catch { reject(new Error('Invalid JSON response from server')); }
                    });
                }
            );
            req.on('error', reject);
            req.write(raw);
            req.end();
        });
    }

    private async _writeFiles(files: GeneratedFile[]) {
        const folders = vscode.workspace.workspaceFolders;
        if (!folders?.length) {
            vscode.window.showErrorMessage('No workspace folder open. Open a folder first (File → Open Folder).');
            return;
        }

        const picked = await vscode.window.showOpenDialog({
            canSelectFiles: false,
            canSelectFolders: true,
            canSelectMany: false,
            defaultUri: folders[0].uri,
            openLabel: 'Write framework here',
        });
        if (!picked?.length) { return; }

        const root = picked[0].fsPath;
        const existing = files.filter(f => fs.existsSync(path.join(root, f.filename)));
        if (existing.length > 0) {
            const choice = await vscode.window.showWarningMessage(
                `${existing.length} file(s) already exist in this folder. Overwrite all?`,
                'Overwrite', 'Cancel'
            );
            if (choice !== 'Overwrite') { return; }
        }

        let written = 0;
        for (const file of files) {
            const dest = path.join(root, file.filename);
            fs.mkdirSync(path.dirname(dest), { recursive: true });
            fs.writeFileSync(dest, file.content, 'utf-8');
            written++;
        }

        this._panel.webview.postMessage({ type: 'written', count: written });
        const action = await vscode.window.showInformationMessage(
            `✅ ${written} files written to ${path.basename(root)}`,
            'Reveal in Explorer'
        );
        if (action === 'Reveal in Explorer') {
            vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(root));
        }
    }

    private _render() {
        const nonce = Array.from({ length: 32 }, () =>
            'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'[
                Math.floor(Math.random() * 62)
            ]
        ).join('');
        const htmlPath = path.join(this._context.extensionUri.fsPath, 'media', 'webview.html');
        let html = fs.readFileSync(htmlPath, 'utf-8');
        html = html.replace(/\{\{NONCE\}\}/g, nonce);
        html = html.replace(/\{\{CSP_SOURCE\}\}/g, this._panel.webview.cspSource);
        this._panel.webview.html = html;
    }

    dispose() {
        AutomationPanel.currentPanel = undefined;
        this._panel.dispose();
        this._disposables.forEach(d => d.dispose());
    }
}
