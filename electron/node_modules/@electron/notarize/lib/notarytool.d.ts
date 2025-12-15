import { NotarizeOptions } from './types.js';
export declare function isNotaryToolAvailable(notarytoolPath?: string): Promise<boolean>;
export declare function notarizeAndWaitForNotaryTool(opts: NotarizeOptions): Promise<void>;
