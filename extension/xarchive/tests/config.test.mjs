import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { Script } from 'node:vm';
import test from 'node:test';
import { CHROME_VERSION, FORK_REVISION, UPSTREAM_VERSION, VERSION } from '../version.js';
import { normalizeBaseUrl, permissionOrigin } from '../lib/library-sync.js';

test('release version and manifest assets are consistent', () => {
  const manifest = JSON.parse(readFileSync(new URL('../manifest.json', import.meta.url), 'utf8'));
  const release = JSON.parse(readFileSync(new URL('../release.json', import.meta.url), 'utf8'));
  assert.equal(manifest.name, 'xarchive · Library Fork');
  assert.equal(manifest.version, CHROME_VERSION);
  assert.equal(manifest.version_name, VERSION);
  assert.equal(release.upstream_version, UPSTREAM_VERSION);
  assert.equal(release.fork_revision, FORK_REVISION);
  assert.equal(VERSION, `${UPSTREAM_VERSION}-fork.${FORK_REVISION}`);
  assert.equal(CHROME_VERSION, `${UPSTREAM_VERSION}.${FORK_REVISION}`);
  for (const path of [manifest.background.service_worker, manifest.options_page, ...Object.values(manifest.icons), ...manifest.content_scripts.flatMap(s => s.js)]) assert.ok(existsSync(new URL(`../${path}`, import.meta.url)), path);
  assert.ok(manifest.host_permissions.includes('https://abs.twimg.com/*'));
  assert.ok(!manifest.host_permissions.includes('<all_urls>'));
  assert.ok(manifest.permissions.includes('scripting'));
  assert.ok(manifest.permissions.includes('activeTab'));
  assert.ok(existsSync(new URL('../library-bridge.js', import.meta.url)));
});

test('private library addresses stay configurable and origin-scoped', () => {
  assert.equal(normalizeBaseUrl('http://library-box.local:32847/'), 'http://library-box.local:32847');
  assert.equal(normalizeBaseUrl('https://x-bookmarks.home.arpa/path/?secret=no#fragment'), 'https://x-bookmarks.home.arpa/path');
  assert.equal(permissionOrigin('http://192.168.50.25:32847'), 'http://192.168.50.25/*');
  assert.throws(() => normalizeBaseUrl('file:///tmp/library'));
});

test('the page bridge reports only the connector for the current private origin', async () => {
  let receive;
  const posted = [];
  const page = {
    addEventListener(type, listener) { if (type === 'message') receive = listener; },
    postMessage(message) { posted.push(message); },
  };
  const connector = { baseUrl: 'http://raspi.local:32847', token: 'never-expose-this', deviceId: 'device-1', serverId: 'server-1' };
  const context = { globalThis: {}, window: page, location: { origin: 'http://raspi.local:32847' }, URL,
    chrome: { runtime: { getManifest: () => ({ version: VERSION }) }, storage: {
      local: { get: async () => ({ xarchive_library_connector: connector }) }, onChanged: { addListener() {} },
    } } };
  new Script(readFileSync(new URL('../library-bridge.js', import.meta.url), 'utf8')).runInNewContext(context);
  receive({ source: page, origin: context.location.origin, data: { channel: 'x-bookmarks-library-page', type: 'ping', requestId: 'one' } });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(posted[0].payload.paired, true);
  assert.equal(posted[0].payload.deviceId, 'device-1');
  assert.equal(JSON.stringify(posted[0]).includes('never-expose-this'), false);
});

test('viewer and browser fixtures have valid inline JavaScript', () => {
  for (const file of ['viewer.html', 'tests/browser-storage.html', 'tests/extension-fixture.html']) {
    const html = readFileSync(new URL(`../${file}`, import.meta.url), 'utf8');
    for (const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new Script(match[1], { filename: file });
  }
});
