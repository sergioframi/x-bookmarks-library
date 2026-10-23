/**
 * xarchive service worker — intentionally minimal.
 *
 * Three responsibilities only:
 *   1. Passively capture auth headers + GraphQL query IDs from X.com
 *      requests via webRequest.onSendHeaders.
 *   2. Open the options page when the extension icon is clicked.
 *   3. Register a dynamic declarativeNetRequest rule at install time
 *      to inject Origin/Referer headers on extension-originated
 *      GraphQL requests (scoped via `initiatorDomains`).
 *
 * All heavy logic (API calls, pagination, storage, export) runs in the
 * options page tab so it is unaffected by service worker lifecycle
 * termination.
 */

import { getSessionUserId, updateCredentials } from './lib/identity.js';
import { getConnector, permissionOrigin, setConnectorSyncState } from './lib/library-sync.js';

const LIBRARY_BRIDGE_ID = 'xarchive-library-bridge';

async function ensureLibraryBridge() {
  const config = await getConnector();
  const existing = await chrome.scripting.getRegisteredContentScripts({ ids: [LIBRARY_BRIDGE_ID] });
  if (existing.length) await chrome.scripting.unregisterContentScripts({ ids: [LIBRARY_BRIDGE_ID] });
  if (!config?.baseUrl) return;
  const matches = [permissionOrigin(config.baseUrl)];
  await chrome.scripting.registerContentScripts([{
    id: LIBRARY_BRIDGE_ID,
    js: ['library-bridge.js'],
    matches,
    runAt: 'document_start',
    persistAcrossSessions: true,
  }]);
  const tabs = await chrome.tabs.query({ url: matches });
  await Promise.all(tabs.map(tab => chrome.scripting.executeScript({
    target: { tabId: tab.id }, files: ['library-bridge.js'],
  }).catch(() => null)));
}

async function startLibrarySync(message, sender) {
  const config = await getConnector();
  if (!config?.baseUrl || !config?.token) throw new Error('The extension is not paired.');
  const configuredOrigin = new URL(config.baseUrl).origin;
  const senderOrigin = sender.tab?.url ? new URL(sender.tab.url).origin : null;
  if (message.origin !== configuredOrigin || senderOrigin !== configuredOrigin) {
    throw new Error('The request came from a different private library.');
  }
  const running = config.syncState?.status === 'running'
    && Date.now() - Date.parse(config.syncState.startedAt || 0) < 2 * 60 * 60 * 1000;
  if (running) return { ok: true, alreadyRunning: true, syncState: config.syncState };
  const mode = message.mode === 'full' ? 'full' : 'quick';
  const startedAt = new Date().toISOString();
  await setConnectorSyncState({ status: 'running', mode, phase: 'Preparing synchronization', startedAt });
  const params = new URLSearchParams({ library_action: 'sync', library_mode: mode, library_origin: configuredOrigin });
  await chrome.tabs.create({ url: chrome.runtime.getURL(`options.html?${params}`), active: false });
  return { ok: true, syncState: { status: 'running', mode, phase: 'Preparing synchronization', startedAt } };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'xarchive:register-library-bridge') {
    ensureLibraryBridge().then(() => sendResponse({ ok: true })).catch(error => sendResponse({ ok: false, error: error.message }));
    return true;
  }
  if (message?.type === 'xarchive:start-library-sync') {
    startLibrarySync(message, sender).then(sendResponse).catch(error => sendResponse({ ok: false, error: error.message }));
    return true;
  }
});

/** Matches bookmark-related GraphQL operations to capture their query IDs. */
const GRAPHQL_PATTERN = /\/graphql\/([^/]+)\/(Bookmarks|BookmarkFoldersSlice|BookmarkFolderTimeline)\b/;

/** Auth-related headers to persist for later use by the options page. */
const CAPTURE_HEADERS = ['authorization', 'x-csrf-token', 'x-client-uuid', 'x-client-transaction-id'];

chrome.webRequest.onSendHeaders.addListener(
  (details) => {
    // Capture real page requests only. Replaying our own calls must not make
    // stale query IDs or credentials appear freshly captured.
    if (!['https://x.com', 'https://twitter.com'].includes(details.initiator)) return;
    const url = new URL(details.url);
    const headerMap = {};

    // Collect relevant auth headers from the outgoing request.
    for (const h of details.requestHeaders || []) {
      if (CAPTURE_HEADERS.includes(h.name.toLowerCase())) {
        headerMap[h.name.toLowerCase()] = h.value;
      }
    }

    // Extract query ID and operation name from GraphQL URL path.
    const match = url.pathname.match(GRAPHQL_PATTERN);
    if (match) {
      const [, queryId, operation] = match;
      headerMap[`queryId_${operation}`] = queryId;
      headerMap[`queryCapturedAt_${operation}`] = Date.now();
    }

    // Capture feature flags from query string for later replay.
    const featuresParam = url.searchParams.get('features');
    if (featuresParam && match) {
      headerMap[`features_${match[2]}`] = featuresParam;
    }

    if (Object.keys(headerMap).length === 0) return;

    // Store captured data namespaced by the logged-in user ID.
    getSessionUserId().then(uid => updateCredentials(uid, { ...headerMap, captured_at: Date.now() }))
      .catch(() => { /* The options page reports missing credentials/storage. */ });
  },
  { urls: ['https://x.com/i/api/graphql/*'], types: ['xmlhttprequest'] },
  ['requestHeaders', 'extraHeaders']
);

/** Open the options page and prefill the private library shown in the active tab. */
chrome.action.onClicked.addListener((tab) => {
  let origin = '';
  try {
    const url = new URL(tab.url || '');
    if (['http:', 'https:'].includes(url.protocol) && !['x.com', 'twitter.com'].includes(url.hostname)) origin = url.origin;
  } catch { /* Open the regular options page when the tab URL is unavailable. */ }
  const query = origin ? `?${new URLSearchParams({ library_origin: origin })}` : '';
  chrome.tabs.create({ url: chrome.runtime.getURL(`options.html${query}`), active: true });
});

/**
 * Install a dynamic declarativeNetRequest rule that injects
 * `Origin: https://x.com` and `Referer: https://x.com/` on the
 * extension's own GraphQL requests.
 *
 * Static rules (rules.json) cannot reference the extension's own
 * origin, so we register a dynamic rule at install time using
 * `chrome.runtime.id` as the `initiatorDomains` value.  This scopes
 * the rule to extension-originated requests only, avoiding
 * interference with normal X.com browsing (Twillot issue #127).
 */
chrome.runtime.onInstalled.addListener(() => {
  ensureLibraryBridge().catch(() => { /* Pairing UI reports registration failures. */ });
  chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: [1],
    addRules: [{
      id: 1,
      priority: 1,
      action: {
        type: 'modifyHeaders',
        requestHeaders: [
          { header: 'Origin', operation: 'set', value: 'https://x.com' },
          { header: 'Referer', operation: 'set', value: 'https://x.com/' },
        ],
      },
      condition: {
        urlFilter: 'https://x.com/i/api/graphql/*',
        resourceTypes: ['xmlhttprequest'],
        initiatorDomains: [chrome.runtime.id],
      },
    }],
  });
});

chrome.runtime.onStartup.addListener(() => {
  ensureLibraryBridge().catch(() => { /* Retried on the next browser start or pairing. */ });
});

ensureLibraryBridge().catch(() => { /* Service-worker startup best effort. */ });
