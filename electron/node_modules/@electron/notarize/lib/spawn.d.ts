/// <reference types="node" resolution-mode="require"/>
import { SpawnOptions } from 'node:child_process';
export interface SpawnResult {
    code: number | null;
    output: string;
}
export declare const spawn: (cmd: string, args?: string[], opts?: SpawnOptions) => Promise<SpawnResult>;
