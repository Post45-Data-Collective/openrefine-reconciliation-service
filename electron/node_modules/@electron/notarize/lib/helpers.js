import debug from 'debug';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
const d = debug('electron-notarize:helpers');
export async function withTempDir(fn) {
    const dir = await fs.promises.mkdtemp(path.resolve(os.tmpdir(), 'electron-notarize-'));
    d('doing work inside temp dir:', dir);
    let result;
    try {
        result = await fn(dir);
    }
    catch (err) {
        d('work failed');
        await fs.promises.rm(dir, { recursive: true, force: true });
        throw err;
    }
    d('work succeeded');
    await fs.promises.rm(dir, { recursive: true, force: true });
    return result;
}
class Secret {
    value;
    constructor(value) {
        this.value = value;
    }
    toString() {
        return this.value;
    }
    inspect() {
        return '******';
    }
}
export function makeSecret(s) {
    return new Secret(s);
}
export function isSecret(s) {
    return s instanceof Secret;
}
export function parseNotarizationInfo(info) {
    const out = {};
    const matchToProperty = (key, r, modifier) => {
        const exec = r.exec(info);
        if (exec) {
            out[key] = modifier ? modifier(exec[1]) : exec[1];
        }
    };
    matchToProperty('uuid', /\n *RequestUUID: (.+?)\n/);
    matchToProperty('date', /\n *Date: (.+?)\n/, (d) => new Date(d));
    matchToProperty('status', /\n *Status: (.+?)\n/);
    matchToProperty('logFileUrl', /\n *LogFileURL: (.+?)\n/);
    matchToProperty('statusCode', /\n *Status Code: (.+?)\n/, (n) => parseInt(n, 10));
    matchToProperty('statusMessage', /\n *Status Message: (.+?)\n/);
    if (out.logFileUrl === '(null)') {
        out.logFileUrl = null;
    }
    return out;
}
//# sourceMappingURL=helpers.js.map