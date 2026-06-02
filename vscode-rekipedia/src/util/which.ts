import { execFile } from 'child_process';

export function which(cmd: string): Promise<string | null> {
  return new Promise((resolve) => {
    const whichCmd = process.platform === 'win32' ? 'where' : 'which';
    execFile(whichCmd, [cmd], (err, stdout) => {
      resolve(err ? null : stdout.trim().split('\n')[0]);
    });
  });
}
