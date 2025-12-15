import debug from 'debug';
import retry from 'promise-retry';
import { checkSignatures } from './check-signature.js';
import { isNotaryToolAvailable, notarizeAndWaitForNotaryTool } from './notarytool.js';
import { stapleApp } from './staple.js';
const d = debug('electron-notarize');
export * from './types.js';
export { validateNotaryToolAuthorizationArgs as validateAuthorizationArgs } from './validate-args.js';
async function notarize({ appPath, ...otherOptions }) {
    await checkSignatures({ appPath });
    d('notarizing using notarytool');
    if (!(await isNotaryToolAvailable())) {
        throw new Error('notarytool is not available, you must be on at least Xcode 13 or provide notarytoolPath');
    }
    await notarizeAndWaitForNotaryTool({
        appPath,
        ...otherOptions,
    });
    await retry(() => stapleApp({ appPath }), {
        retries: 3,
    });
}
export { notarize };
//# sourceMappingURL=index.js.map