const CONFIG_KEY = 'xarchive_library_connector';
const MAX_LOG_ENTRIES = 200;
let connectorWrite = Promise.resolve();

export function normalizeBaseUrl(value) {
  const parsed = new URL(String(value || '').trim());
  if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('Use una URL http:// o https://.');
  parsed.username = '';
  parsed.password = '';
  parsed.hash = '';
  parsed.search = '';
  return parsed.toString().replace(/\/$/, '');
}

export function permissionOrigin(baseUrl) {
  const parsed = new URL(baseUrl);
  return `${parsed.protocol}//${parsed.hostname}/*`;
}

export async function getConnector() {
  return (await chrome.storage.local.get(CONFIG_KEY))[CONFIG_KEY] || null;
}

async function saveConnector(value) {
  await chrome.storage.local.set({ [CONFIG_KEY]: value });
  return value;
}

function updateConnector(change) {
  const operation = connectorWrite.catch(() => {}).then(async () => {
    const config = await getConnector();
    if (!config) throw new Error('Pair the extension with the private library first.');
    await change(config);
    return saveConnector(config);
  });
  connectorWrite = operation;
  return operation;
}

export async function setConnectorSyncState(value) {
  return updateConnector(config => {
    config.syncState = { ...value, updatedAt: new Date().toISOString() };
  });
}

export async function appendConnectorLog(message, level = 'info') {
  const entry = {
    at: new Date().toISOString(),
    level: ['info', 'warn', 'error', 'success'].includes(level) ? level : 'info',
    message: String(message || '').slice(0, 1000),
  };
  try {
    return await updateConnector(config => {
      config.logs = [...(Array.isArray(config.logs) ? config.logs : []), entry].slice(-MAX_LOG_ENTRIES);
    });
  } catch {
    return null;
  }
}

export async function setConnectorDiagnostics(value) {
  try {
    return await updateConnector(config => {
      config.diagnostics = { ...value, updatedAt: new Date().toISOString() };
    });
  } catch {
    return null;
  }
}

export async function pairConnector(baseUrl, code, deviceName, extensionVersion) {
  const normalized = normalizeBaseUrl(baseUrl);
  const granted = await chrome.permissions.request({ origins: [permissionOrigin(normalized)] });
  if (!granted) throw new Error('Chrome did not grant access to the private library.');
  const response = await fetch(`${normalized}/api/v1/xarchive/pair`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, name: deviceName || 'Chrome', extension_version: extensionVersion }),
    signal: AbortSignal.timeout(15_000),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Pairing rejected (HTTP ${response.status}).`);
  const config = await saveConnector({
    baseUrl: normalized,
    deviceId: data.device_id,
    token: data.device_token,
    accountUserId: data.account_user_id || null,
    serverId: data.server_id || null,
    pairedAt: new Date().toISOString(),
    lastSync: null,
    logs: [],
    diagnostics: null,
    syncState: { status: 'ready', updatedAt: new Date().toISOString() },
  });
  const registration = await chrome.runtime.sendMessage({ type: 'xarchive:register-library-bridge' });
  if (!registration?.ok) throw new Error(registration?.error || 'Could not activate the connection with the page.');
  return config;
}

async function authorizedFetch(path, options = {}) {
  const config = await getConnector();
  if (!config?.token || !config?.baseUrl) throw new Error('Pair the extension with the private library first.');
  const response = await fetch(`${config.baseUrl}${path}`, {
    ...options,
    headers: { ...(options.headers || {}), Authorization: `Bearer ${config.token}` },
  });
  if (response.status === 401) throw new Error('This device was revoked or its token is no longer valid.');
  return { response, config };
}

export async function fetchBootstrap() {
  const { response } = await authorizedFetch('/api/v1/xarchive/bootstrap', {
    signal: AbortSignal.timeout(60_000),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Could not download the initial archive (HTTP ${response.status}).`);
  }
  return response.json();
}

export async function syncArchive(archive, snapshot, scanId) {
  const { response } = await authorizedFetch('/api/v1/xarchive/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scan_id: scanId, archive, snapshot: snapshot || null }),
    signal: AbortSignal.timeout(180_000),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Synchronization rejected (HTTP ${response.status}).`);
  await updateConnector(config => {
    config.lastSync = { at: new Date().toISOString(), scanId, receipt: data };
  });
  return data;
}
