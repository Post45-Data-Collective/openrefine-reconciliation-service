import { spawn as cpSpawn } from 'node:child_process';
import debug from 'debug';
import { isSecret } from './helpers.js';
const d = debug('electron-notarize:spawn');
export const spawn = (cmd, args = [], opts = {}) => {
    d('spawning cmd:', cmd, 'args:', args.map((arg) => (isSecret(arg) ? '*********' : arg)), 'opts:', opts);
    const child = cpSpawn(cmd, args, opts);
    const out = [];
    const dataHandler = (data) => out.push(data.toString());
    child.stdout.on('data', dataHandler);
    child.stderr.on('data', dataHandler);
    return new Promise((resolve, reject) => {
        child.on('error', (err) => {
            reject(err);
        });
        child.on('exit', (code) => {
            d(`cmd ${cmd} terminated with code: ${code}`);
            resolve({
                code,
                output: out.join(''),
            });
        });
    });
};
//# sourceMappingURL=spawn.js.map