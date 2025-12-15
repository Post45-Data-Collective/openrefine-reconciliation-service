import { NotarizeOptions } from './types.js';
export * from './types.js';
export { validateNotaryToolAuthorizationArgs as validateAuthorizationArgs } from './validate-args.js';
/**
 * Sends your app to Apple for notarization with `notarytool` and staples a successful
 * notarization result to the app bundle. This includes your {@link NotaryToolNotarizeAppOptions.appPath | appPath}
 * as well as one of three valid credential authentication strategies.
 *
 * See {@link NotaryToolCredentials} for authentication options.
 *
 * @category Core
 * @param args Options for notarization
 * @returns The Promise resolves once notarization is complete. Note that this may take a few minutes.
 */
declare function notarize(args: NotarizeOptions): Promise<void>;
export { notarize };
