(() => {
  if (globalThis.__xarchiveLibraryBridge) return;
  globalThis.__xarchiveLibraryBridge = true;

  const PAGE_CHANNEL = 'x-bookmarks-library-page';
  const EXTENSION_CHANNEL = 'xarchive-connector';
  const CONFIG_KEY = 'xarchive_library_connector';

  function sameOrigin(config) {
    try { return new URL(config?.baseUrl).origin === location.origin; }
    catch { return false; }
  }

  function publicStatus(config) {
    return {
      installed: true,
      version: chrome.runtime.getManifest().version,
      paired: Boolean(config?.token && sameOrigin(config)),
      baseUrl: sameOrigin(config) ? config.baseUrl : null,
      deviceId: sameOrigin(config) ? config.deviceId : null,
      serverId: sameOrigin(config) ? config.serverId : null,
      pairedAt: sameOrigin(config) ? config.pairedAt : null,
      lastSync: sameOrigin(config) ? config.lastSync : null,
      syncState: sameOrigin(config) ? config.syncState : null,
      logs: sameOrigin(config) && Array.isArray(config?.logs) ? config.logs.slice(-200) : [],
      diagnostics: sameOrigin(config) ? config.diagnostics : null,
    };
  }

  function reply(type, requestId, payload = {}, error = null) {
    window.postMessage({ channel: EXTENSION_CHANNEL, version: 1, type, requestId, payload, error }, location.origin);
  }

  async function status() {
    const stored = await chrome.storage.local.get(CONFIG_KEY);
    return publicStatus(stored[CONFIG_KEY] || null);
  }

  window.addEventListener('message', async event => {
    if (event.source !== window || event.origin !== location.origin || event.data?.channel !== PAGE_CHANNEL) return;
    const { type, requestId, payload = {} } = event.data;
    try {
      if (type === 'ping') return reply('status', requestId, await status());
      if (type === 'sync') {
        const current = await status();
        if (!current.paired) throw new Error('The extension is not paired with this private library.');
        const mode = payload.mode === 'full' ? 'full' : 'quick';
        const result = await chrome.runtime.sendMessage({ type: 'xarchive:start-library-sync', mode, origin: location.origin });
        if (!result?.ok) throw new Error(result?.error || 'Could not start synchronization.');
        return reply('sync-accepted', requestId, result);
      }
    } catch (error) {
      reply('error', requestId, {}, error?.message || String(error));
    }
  });

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== 'local' || !changes[CONFIG_KEY]) return;
    const config = changes[CONFIG_KEY].newValue || null;
    if (sameOrigin(config)) reply('status', null, publicStatus(config));
  });
})();
