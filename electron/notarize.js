const { notarize } = require('@electron/notarize');

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context;
  if (electronPlatformName !== 'darwin') {
    return;
  }

  const appName = context.packager.appInfo.productFilename;

  const appleId = process.env.APPLE_ID;
  const appleIdPassword = process.env.APPLE_ID_PASSWORD;

  if (!appleId || !appleIdPassword) {
    console.log('Skipping notarization: APPLE_ID or APPLE_ID_PASSWORD not set');
    return;
  }

  console.log(`Notarizing ${appName}...`);

  return await notarize({
    appBundleId: 'com.post45.bookreconciler',
    appPath: `${appOutDir}/${appName}.app`,
    appleId: appleId,
    appleIdPassword: appleIdPassword,
    teamId: process.env.APPLE_TEAM_ID
  });
};
