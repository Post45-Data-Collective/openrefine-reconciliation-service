import { NotaryToolApiKeyCredentials, NotaryToolCredentials, NotaryToolKeychainCredentials, NotaryToolPasswordCredentials } from './types.js';
export declare function isNotaryToolPasswordCredentials(opts: NotaryToolCredentials): opts is NotaryToolPasswordCredentials;
export declare function isNotaryToolApiKeyCredentials(opts: NotaryToolCredentials): opts is NotaryToolApiKeyCredentials;
export declare function isNotaryToolKeychainCredentials(opts: NotaryToolCredentials): opts is NotaryToolKeychainCredentials;
/**
 * @internal
 */
export declare function validateNotaryToolAuthorizationArgs(opts: NotaryToolCredentials): NotaryToolCredentials;
