export function isNotaryToolPasswordCredentials(opts) {
    const creds = opts;
    return (creds.appleId !== undefined || creds.appleIdPassword !== undefined || creds.teamId !== undefined);
}
export function isNotaryToolApiKeyCredentials(opts) {
    const creds = opts;
    return (creds.appleApiIssuer !== undefined ||
        creds.appleApiKey !== undefined ||
        creds.appleApiKeyId !== undefined);
}
export function isNotaryToolKeychainCredentials(opts) {
    const creds = opts;
    return creds.keychain !== undefined || creds.keychainProfile !== undefined;
}
/**
 * @internal
 */
export function validateNotaryToolAuthorizationArgs(opts) {
    const isPassword = isNotaryToolPasswordCredentials(opts);
    const isApiKey = isNotaryToolApiKeyCredentials(opts);
    const isKeychain = isNotaryToolKeychainCredentials(opts);
    if ((isPassword ? 1 : 0) + (isApiKey ? 1 : 0) + (isKeychain ? 1 : 0) > 1) {
        throw new Error('Cannot use password credentials, API key credentials and keychain credentials at once');
    }
    if (isPassword) {
        const passwordCreds = opts;
        if (!passwordCreds.appleId) {
            throw new Error('The appleId property is required when using notarization with password credentials');
        }
        else if (!passwordCreds.appleIdPassword) {
            throw new Error('The appleIdPassword property is required when using notarization with password credentials');
        }
        else if (!passwordCreds.teamId) {
            throw new Error('The teamId property is required when using notarization with password credentials');
        }
        return passwordCreds;
    }
    if (isApiKey) {
        const apiKeyCreds = opts;
        if (!apiKeyCreds.appleApiKey) {
            throw new Error('The appleApiKey property is required when using notarization with ASC credentials');
        }
        else if (!apiKeyCreds.appleApiKeyId) {
            throw new Error('The appleApiKeyId property is required when using notarization with ASC credentials');
        }
        return apiKeyCreds;
    }
    if (isKeychain) {
        const keychainCreds = opts;
        if (!keychainCreds.keychainProfile) {
            throw new Error('The keychainProfile property is required when using notarization with keychain credentials');
        }
        return keychainCreds;
    }
    throw new Error('No authentication properties provided (e.g. appleId, appleApiKey, keychain)');
}
//# sourceMappingURL=validate-args.js.map