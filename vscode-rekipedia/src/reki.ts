import { execFile, spawn } from 'child_process';

export function runReki(reki: string, args: string[], cwd: string): Promise<string> {
  return new Promise((resolve, reject) => {
    execFile(reki, args, { cwd, maxBuffer: 10 * 1024 * 1024 }, (err, stdout, stderr) => {
      if (err) reject(new Error(stderr || err.message));
      else resolve(stdout);
    });
  });
}

export function streamReki(
  reki: string,
  args: string[],
  cwd: string,
  onChunk: (line: string) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const child = spawn(reki, args, { cwd });
    let buf = '';
    child.stdout.on('data', (data: Buffer) => {
      buf += data.toString();
      const lines = buf.split('\n');
      buf = lines.pop() ?? '';
      for (const line of lines) onChunk(line);
    });
    child.stderr.on('data', (data: Buffer) => {
      // surface errors live too
      onChunk(`__error__:${data.toString()}`);
    });
    child.on('close', (code) => {
      if (buf) onChunk(buf);
      if (code === 0) resolve();
      else reject(new Error(`reki exited with code ${code}`));
    });
    child.on('error', reject);
  });
}
