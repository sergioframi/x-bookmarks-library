const $ = (s) => document.querySelector(s),
  $$ = (s) => [...document.querySelectorAll(s)];
const state = {
  csrf: "",
  taxonomy: null,
  taxonomyDiscovery: null,
  query: "",
  page: 1,
  pageSize: 30,
  filters: { categories: [], tags: [], authors: [], content_types: [] },
  generation: 0,
  current: [],
  total: 0,
  mode: "timeline",
  views: [],
  activeViewId: null,
  viewEditorMode: "create",
  editingColumnId: null,
  pendingDelete: null,
};
const cache = new Map();
let debounceTimer = null,
  textController = null,
  semanticController = null;
const uiLocale = () => window.xbI18n?.locale() || "es";
const tr = (value) =>
  window.xbI18n?.translate(String(value ?? "")) ?? String(value ?? "");
const typeLabels = {
  tool: "Herramienta",
  article: "Artículo",
  thread: "Hilo",
  tutorial: "Tutorial",
  reference: "Referencia",
  video: "Vídeo",
  image: "Imagen",
  other: "Otro",
};
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const safeUrl = (value) => {
  try {
    const u = new URL(value);
    return ["http:", "https:"].includes(u.protocol) ? u.href : "";
  } catch {
    return "";
  }
};
const themeKey = "x-bookmarks-theme",
  paletteKey = "x-bookmarks-palette",
  paletteMeta = {
    mono: { name: "Monocroma", light: "#e8eaed", dark: "#343a42" },
    ice: { name: "Azul hielo", light: "#e3eff8", dark: "#304255" },
    lavender: { name: "Lavanda nube", light: "#ece8f6", dark: "#433a56" },
    rose: { name: "Rosa cuarzo", light: "#f2e7ec", dark: "#4b3942" },
    coral: { name: "Arena y coral", light: "#f3e9e5", dark: "#4b3b36" },
  };
function updateThemeColor() {
  const palette =
      paletteMeta[document.documentElement.dataset.palette] || paletteMeta.ice,
    dark = document.documentElement.dataset.theme === "dark",
    themeColor = $("#theme-color");
  if (themeColor) themeColor.content = dark ? palette.dark : palette.light;
}
function setTheme(theme, { persist = false } = {}) {
  const dark = theme === "dark",
    value = dark ? "dark" : "light";
  document.documentElement.dataset.theme = value;
  const button = $("#theme-toggle"),
    icon = $("#theme-icon"),
    label = dark ? "Activar tema claro" : "Activar tema oscuro";
  if (icon) icon.textContent = dark ? "☀" : "☾";
  if (button) {
    button.setAttribute("aria-label", label);
    button.setAttribute("aria-pressed", String(dark));
    button.dataset.tooltip = dark ? "Tema claro" : "Tema oscuro";
  }
  updateThemeColor();
  if (persist)
    try {
      localStorage.setItem(themeKey, value);
    } catch {}
}
function setPalette(palette, { persist = false } = {}) {
  const value = paletteMeta[palette] ? palette : "ice",
    meta = paletteMeta[value];
  document.documentElement.dataset.palette = value;
  $$("[data-palette-choice]").forEach((button) => {
    const active = button.dataset.paletteChoice === value;
    button.classList.toggle("active", active);
    button.setAttribute("aria-checked", String(active));
  });
  const trigger = $("#palette-toggle");
  if (trigger) {
    trigger.setAttribute(
      "aria-label",
      `Previsualizar paletas. Actual: ${meta.name}`,
    );
    trigger.dataset.tooltip = meta.name;
  }
  updateThemeColor();
  if (persist)
    try {
      localStorage.setItem(paletteKey, value);
    } catch {}
}
setTheme(document.documentElement.dataset.theme);
setPalette(document.documentElement.dataset.palette);
$("#theme-toggle").addEventListener("click", () =>
  setTheme(
    document.documentElement.dataset.theme === "dark" ? "light" : "dark",
    { persist: true },
  ),
);
$("#palette-toggle").addEventListener("click", (event) => {
  event.stopPropagation();
  const menu = $("#palette-menu"),
    open = menu.classList.toggle("hidden") === false;
  event.currentTarget.setAttribute("aria-expanded", String(open));
});
$$("[data-palette-choice]").forEach((button) =>
  button.addEventListener("click", () => {
    setPalette(button.dataset.paletteChoice, { persist: true });
    toast(`Paleta: ${paletteMeta[button.dataset.paletteChoice].name}`);
  }),
);
document.addEventListener("pointerdown", (event) => {
  if (!event.target.closest(".appearance-picker")) {
    $("#palette-menu").classList.add("hidden");
    $("#palette-toggle").setAttribute("aria-expanded", "false");
  }
});
document.addEventListener("keydown", (event) => {
  if (
    event.key === "Escape" &&
    !$("#palette-menu").classList.contains("hidden")
  ) {
    $("#palette-menu").classList.add("hidden");
    $("#palette-toggle").setAttribute("aria-expanded", "false");
    $("#palette-toggle").focus();
  }
});
function toast(message) {
  const e = $("#toast");
  e.textContent = tr(message);
  e.classList.add("show");
  setTimeout(() => e.classList.remove("show"), 2200);
}
async function api(path, options = {}, cacheMs = 0) {
  const key = path;
  const saved = cache.get(key);
  if (!options.method && saved && Date.now() - saved.time < cacheMs)
    return saved.data;
  const headers = { ...(options.headers || {}) };
  if (state.csrf && options.method && options.method !== "GET")
    headers["X-CSRF-Token"] = state.csrf;
  if (options.body) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers,
  });
  if (response.status === 401) {
    $("#login").classList.remove("hidden");
    throw new Error("Sesión caducada");
  }
  if (!response.ok) {
    let message = response.statusText;
    try {
      message = (await response.json()).detail || message;
    } catch {}
    throw new Error(tr(message));
  }
  const data = await response.json();
  if (!options.method && cacheMs) cache.set(key, { time: Date.now(), data });
  return data;
}
async function authenticate() {
  let session;
  try {
    session = await api("/api/session");
  } catch {
    $("#login").classList.remove("hidden");
    return;
  }
  state.csrf = session.csrf;
  $("#login").classList.add("hidden");
  try {
    await window.xbOnboarding.resume();
  } catch (error) {
    toast(`No se pudo cargar la biblioteca: ${error.message}`);
  }
}
$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#login-error").textContent = "";
  try {
    const data = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({
        username: $("#login-user").value,
        password: $("#login-pass").value,
      }),
    });
    state.csrf = data.csrf;
    $("#login").classList.add("hidden");
    await window.xbOnboarding.resume();
  } catch (error) {
    $("#login-error").textContent = error.message;
  }
});
$("#logout").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  location.reload();
});
$("#password-button").addEventListener("click", () => {
  $("#password-dialog").showModal();
  requestAnimationFrame(() => $("#current-password").focus());
});
$("#close-password").addEventListener("click", () =>
  $("#password-dialog").close(),
);
$("#password-dialog").addEventListener("close", () => {
  $("#password-form").reset();
  $("#password-error").textContent = "";
});
$("#password-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const current = $("#current-password").value,
    next = $("#new-password").value,
    confirmation = $("#confirm-password").value,
    error = $("#password-error"),
    button = $("#save-password");
  error.textContent = "";
  if (next.length < 12) {
    error.textContent =
      "La nueva contraseña debe tener al menos 12 caracteres.";
    return;
  }
  if (next !== confirmation) {
    error.textContent = "Las contraseñas nuevas no coinciden.";
    return;
  }
  button.disabled = true;
  try {
    const result = await api("/api/account/password", {
      method: "POST",
      body: JSON.stringify({ current_password: current, new_password: next }),
    });
    state.csrf = result.csrf;
    $("#password-dialog").close();
    toast("Contraseña actualizada");
  } catch (problem) {
    error.textContent = problem.message;
  } finally {
    button.disabled = false;
  }
});
const connectorRequests = new Map();
let connectorStatus = null,
  connectorDevices = null,
  serverEnrichment = null,
  connectorPoll = null;
function connectorRequest(type, payload = {}, timeout = 1200) {
  return new Promise((resolve, reject) => {
    const requestId =
      globalThis.crypto?.randomUUID?.() ||
      `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const timer = setTimeout(() => {
      connectorRequests.delete(requestId);
      reject(new Error("La extensión no respondió"));
    }, timeout);
    connectorRequests.set(requestId, { resolve, reject, timer });
    window.postMessage(
      {
        channel: "x-bookmarks-library-page",
        version: 1,
        type,
        requestId,
        payload,
      },
      location.origin,
    );
  });
}
window.addEventListener("message", (event) => {
  if (
    event.source !== window ||
    event.origin !== location.origin ||
    event.data?.channel !== "xarchive-connector"
  )
    return;
  const message = event.data;
  if (message.requestId && connectorRequests.has(message.requestId)) {
    const pending = connectorRequests.get(message.requestId);
    clearTimeout(pending.timer);
    connectorRequests.delete(message.requestId);
    message.error
      ? pending.reject(new Error(message.error))
      : pending.resolve(message.payload);
  }
  if (message.type === "status") {
    connectorStatus = message.payload;
    renderConnectorStatus();
    renderSyncInspection();
  }
});
async function detectConnector() {
  try {
    connectorStatus = await connectorRequest("ping", {}, 900);
  } catch {
    connectorStatus = null;
  }
  renderConnectorStatus();
  return connectorStatus;
}
function startConnectorPolling() {
  if (connectorPoll) return;
  connectorPoll = setInterval(async () => {
    if (document.hidden) return;
    await Promise.allSettled([detectConnector(), refreshEnrichmentStatus()]);
  }, 4000);
}
function connectorClass(value) {
  return value === "running"
    ? "busy"
    : value === "error"
      ? "error"
      : value === "online"
        ? "online"
        : "";
}
function syncDate(value) {
  if (!value) return null;
  const normalized = String(value).includes("T")
    ? String(value)
    : `${String(value).replace(" ", "T")}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}
async function refreshEnrichmentStatus() {
  serverEnrichment = await api("/api/enrichment");
  renderConnectorStatus();
  renderSyncInspection();
  return serverEnrichment;
}
function renderSyncInspection() {
  const root = $("#server-enrichment"),
    job = serverEnrichment?.job;
  if (!root) return;
  root.classList.toggle("hidden", !job);
  if (job) {
    const taxonomyPhase = String(job.phase || "").startsWith("taxonomy"),
      completed = taxonomyPhase
        ? Number(job.completed || 0)
        : Number(serverEnrichment.embeddings || job.completed || 0),
      total = taxonomyPhase
        ? Number(job.total || 0)
        : Number(serverEnrichment.documents || job.total || 0),
      percent = total ? Math.min(100, Math.round((completed * 100) / total)) : 0;
    $("#server-progress-title").textContent =
      job.message || "Procesando la biblioteca";
    $("#server-progress-percent").textContent = total ? `${percent}%` : "";
    $("#server-progress-bar").style.width = `${percent}%`;
    const heartbeat = syncDate(job.heartbeat_at);
    $("#server-progress-detail").textContent = [
      total ? `${completed.toLocaleString(uiLocale())} de ${total.toLocaleString(uiLocale())}` : "",
      job.status,
      heartbeat ? `actualizado ${heartbeat.toLocaleTimeString(uiLocale())}` : "",
    ]
      .filter(Boolean)
      .join(" · ");
  }
  const diagnostics = connectorStatus?.diagnostics || {},
    operations = diagnostics.queryOperations || {},
    fields = [
      ["Extensión", connectorStatus?.version || "No detectada"],
      ["Servidor", serverEnrichment?.busy ? "Ocupado" : "Disponible"],
      ["Cuenta de X", diagnostics.accountDetected ? "Detectada" : "No detectada"],
      ["Credenciales", diagnostics.credentialsAvailable ? "Disponibles" : "No disponibles"],
      ["Consulta Bookmarks", operations.Bookmarks ? "Disponible" : "Pendiente"],
      ["Embeddings", `${Number(serverEnrichment?.embeddings || 0).toLocaleString(uiLocale())} / ${Number(serverEnrichment?.documents || 0).toLocaleString(uiLocale())}`],
      ["Taxonomía", serverEnrichment?.taxonomy_state || "—"],
      ["Último latido", syncDate(job?.heartbeat_at)?.toLocaleString(uiLocale()) || "—"],
    ];
  $("#sync-diagnostics").innerHTML = fields
    .map(
      ([label, value]) =>
        `<div class="sync-diagnostic"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`,
    )
    .join("");
  const extensionEvents = (connectorStatus?.logs || []).map((entry, index) => ({
      id: `extension-${index}-${entry.at}`,
      at: entry.at,
      source: "extensión",
      level: entry.level || "info",
      message: entry.message,
    })),
    serverEvents = (serverEnrichment?.events || []).map((entry) => ({
      id: `server-${entry.id}`,
      at: entry.created_at,
      source: entry.source || "servidor",
      level: entry.level || "info",
      message: entry.message,
    })),
    events = [...extensionEvents, ...serverEvents]
      .sort((left, right) => (syncDate(left.at)?.getTime() || 0) - (syncDate(right.at)?.getTime() || 0))
      .slice(-150);
  $("#sync-combined-log").innerHTML = events.length
    ? events
        .map((entry) => {
          const date = syncDate(entry.at);
          return `<div class="sync-log-entry ${esc(entry.level)}"><time>${date ? date.toLocaleTimeString(uiLocale()) : "—"}</time><b>${esc(entry.source)}</b><span>${esc(entry.message)}</span></div>`;
        })
        .join("")
    : '<p class="handle">Todavía no hay eventos registrados.</p>';
}
function renderConnectorStatus() {
  const detected = Boolean(connectorStatus?.installed),
    paired = Boolean(connectorStatus?.paired),
    job = connectorStatus?.syncState || {},
    devicesLoaded = Array.isArray(connectorDevices?.devices),
    matchingDevice = connectorDevices?.devices?.find(
      (device) => device.id === connectorStatus?.deviceId,
    ),
    revoked = Boolean(matchingDevice?.revoked_at),
    missingDevice = Boolean(paired && devicesLoaded && !matchingDevice),
    wrongServer = Boolean(
      paired &&
        connectorStatus?.serverId &&
        connectorDevices?.instance_id &&
        connectorStatus.serverId !== connectorDevices.instance_id,
    ),
    ready = paired && !revoked && !missingDevice && !wrongServer,
    serverBusy = Boolean(serverEnrichment?.busy);
  let level = "",
    title = "Extensión no detectada",
    detail = `Instálala o conéctala a ${location.origin}.`;
  if (detected && !paired) {
    title = "Extensión instalada, sin conectar";
    detail = "Empareja este navegador con la dirección privada actual.";
  }
  if (ready) {
    level = "online";
    title = "Extensión conectada";
    detail = `Versión ${connectorStatus.version}${matchingDevice ? ` · ${matchingDevice.name}` : ""}.`;
  }
  if (wrongServer) {
    level = "error";
    title = "Conectada a otra instalación";
    detail = "Vuelve a emparejar la extensión con esta biblioteca privada.";
  } else if (revoked) {
    level = "error";
    title = "Dispositivo revocado";
    detail = "Genera un código nuevo para volver a conectar este Chrome.";
  } else if (missingDevice) {
    level = "error";
    title = "Dispositivo eliminado";
    detail = "Genera un código nuevo para volver a conectar este Chrome.";
  } else if (ready && job.status === "running") {
    level = "running";
    title = "Sincronización en curso";
    detail =
      job.mode === "full"
        ? "Revisando toda la colección y las carpetas."
        : "Buscando guardados recientes.";
  } else if (ready && serverBusy) {
    level = "running";
    title = "Procesamiento local en curso";
    detail = serverEnrichment?.job?.message || "La Raspberry está procesando la biblioteca.";
  } else if (ready && job.status === "error") {
    level = "error";
    title = "La última sincronización falló";
    detail = job.error || "Abre xarchive para revisar la sesión de X.";
  } else if (ready && job.status === "completed") {
    const added = job.summary?.import?.new || 0,
      updated = job.summary?.import?.updated || 0;
    title = "Sincronización completada";
    detail = `${added} nuevos · ${updated} actualizados · ${job.finishedAt ? new Date(job.finishedAt).toLocaleString(uiLocale()) : "ahora"}.`;
  }
  for (const dot of [$("#sync-dot"), $("#sync-panel-dot")]) {
    dot.className = `sync-dot ${connectorClass(level)}`.trim();
  }
  $("#extension-button").title = `Sincronización: ${title.toLowerCase()}`;
  $("#sync-local-title").textContent = title;
  $("#sync-local-detail").textContent = detail;
  $("#sync-actions").classList.toggle("hidden", !ready);
  const running = ready && (job.status === "running" || serverBusy);
  $("#sync-quick").disabled = running;
  $("#sync-full").disabled = running;
  $("#sync-progress").classList.toggle("hidden", !running);
  if (running) {
    $("#sync-progress-label").textContent =
      job.status === "running"
        ? job.phase || "Sincronizando…"
        : serverEnrichment?.job?.message || "Procesando localmente…";
    $("#sync-progress-count").textContent = [
      job.bookmarks ? `${job.bookmarks} guardados` : "",
      job.pages ? `${job.pages} páginas` : "",
      job.folders && job.folders !== "--" ? `${job.folders} carpetas` : "",
      job.speed && job.speed !== "--" ? job.speed : "",
      job.elapsedSeconds != null
        ? `${Math.floor(job.elapsedSeconds / 60)}:${String(Math.floor(job.elapsedSeconds % 60)).padStart(2, "0")}`
        : "",
    ]
      .filter(Boolean)
      .join(" · ");
  }
  if (ready && !$("#extension-setup").dataset.userToggled)
    $("#extension-setup").open = false;
}
async function startLibrarySync(mode) {
  if (serverEnrichment?.busy) {
    toast("Ya hay una sincronización o enriquecimiento en curso");
    return null;
  }
  try {
    const result = await connectorRequest("sync", { mode }, 5000);
    connectorStatus = {
      ...connectorStatus,
      syncState: result.syncState || connectorStatus?.syncState,
    };
    renderConnectorStatus();
    toast(result.alreadyRunning ? "La sincronización ya estaba en curso" : mode === "full" ? "Revisión completa iniciada" : "Sincronización iniciada");
    return result;
  } catch (error) {
    toast(error.message);
    await detectConnector();
    return null;
  }
}
function renderServerSync(latest) {
  const root = $("#sync-server-status");
  if (!latest) {
    root.textContent = "Todavía no hay sincronizaciones registradas.";
    return;
  }
  const imported = latest.import || {},
    lifecycle = latest.lifecycle || {};
  root.innerHTML = `<strong>${esc(latest.device_name || "Dispositivo")}</strong><br>${latest.started_at ? new Date(latest.started_at).toLocaleString(uiLocale()) : ""} · ${esc(latest.status)}<br>${Number(imported.new || 0)} nuevos · ${Number(imported.updated || 0)} actualizados · ${Number(lifecycle.removed || 0)} eliminados confirmados`;
}
$("#extension-button").addEventListener("click", async () => {
  $("#extension-dialog").showModal();
  try {
    await loadExtensionPanel();
  } catch (error) {
    $("#extension-package").textContent = error.message;
  }
});
$("#close-extension").addEventListener("click", () =>
  $("#extension-dialog").close(),
);
$("#extension-setup").addEventListener("toggle", (event) => {
  if (event.isTrusted) event.currentTarget.dataset.userToggled = "true";
});
$("#sync-quick").addEventListener("click", () => startLibrarySync("quick"));
$("#sync-full").addEventListener("click", () => startLibrarySync("full"));
$("#new-pairing-code").addEventListener("click", async () => {
  try {
    const result = await api("/api/v1/xarchive/pairing-codes", {
      method: "POST",
    });
    const box = $("#pairing-code");
    let copied = false;
    try {
      await navigator.clipboard.writeText(result.code);
      copied = true;
    } catch {}
    box.innerHTML = `<strong>${esc(result.code)}</strong><small>${esc(location.origin)} · caduca ${new Date(result.expires_at).toLocaleTimeString(uiLocale(), { hour: "2-digit", minute: "2-digit" })}${copied ? " · código copiado" : ""}</small>`;
    box.classList.remove("hidden");
    $("#extension-setup").open = true;
  } catch (error) {
    toast(error.message);
  }
});
async function bootstrap(showDiscovery = true) {
  const [taxonomy, stats, views, discovery] = await Promise.all([
    api("/api/taxonomy", {}, 300000),
    api("/api/stats", {}, 30000),
    api("/api/views"),
    api("/api/taxonomy/discovery"),
  ]);
  state.taxonomy = taxonomy;
  state.taxonomyDiscovery = discovery;
  state.views = views.views;
  $("#stats").textContent =
    `${stats.bookmarks.toLocaleString(uiLocale())} bookmarks · ${stats.embeddings.toLocaleString(uiLocale())} embeddings`;
  renderFilters();
  renderViewsNavigation();
  renderTaxonomyDiscovery(discovery);
  startConnectorPolling();
  detectConnector();
  await searchNow();
  const preferred = state.views.find((view) => view.is_default);
  if (preferred) switchWorkspace("views", preferred.id);
  if (
    showDiscovery &&
    discovery.state === "draft" &&
    !$("#taxonomy-dialog").open
  )
    $("#taxonomy-dialog").showModal();
}
function renderTaxonomyDiscovery(discovery) {
  state.taxonomyDiscovery = discovery;
  const active = discovery.state === "active",
    draft = discovery.state === "draft",
    button = $("#taxonomy-button"),
    generate = $("#discover-taxonomy"),
    form = $("#taxonomy-discovery-form"),
    status = $("#taxonomy-discovery-status");
  button.classList.toggle("hidden", active);
  generate.classList.toggle("hidden", draft);
  form.classList.toggle("hidden", !draft);
  if (active) {
    status.textContent = "La taxonomía personalizada está activa.";
    return;
  }
  if (!draft) {
    status.textContent =
      "Cuando termine la primera importación puedes descubrir aquí los temas de tu biblioteca.";
    return;
  }
  status.textContent = `${discovery.candidates.length} categorías propuestas. Revisa los nombres antes de aplicarlas.`;
  $("#taxonomy-candidates").innerHTML = discovery.candidates
    .map(
      (candidate) =>
        `<article class="taxonomy-candidate"><label class="taxonomy-choice"><input type="checkbox" data-taxonomy-enabled="${candidate.id}" checked><span><strong>${candidate.bookmark_count.toLocaleString(uiLocale())} bookmarks</strong><small>${Number(candidate.cohesion).toLocaleString(uiLocale(), { maximumFractionDigits: 2 })} de cohesión</small></span></label><label>Nombre<input data-taxonomy-name="${candidate.id}" maxlength="100" value="${esc(candidate.name)}" required></label><label>Descripción<textarea data-taxonomy-description="${candidate.id}" maxlength="500" rows="2">${esc(candidate.description)}</textarea></label><div class="taxonomy-keywords">${candidate.keywords.map((word) => `<span>${esc(word)}</span>`).join("")}</div><details><summary>Ver ejemplos</summary>${candidate.examples.map((example) => `<p><strong>${example.author_handle ? `@${esc(example.author_handle)}` : "Bookmark"}</strong> ${esc(example.text).slice(0, 280)}</p>`).join("")}</details></article>`,
    )
    .join("");
}
async function openTaxonomyDiscovery() {
  if (!state.taxonomyDiscovery)
    state.taxonomyDiscovery = await api("/api/taxonomy/discovery");
  renderTaxonomyDiscovery(state.taxonomyDiscovery);
  $("#taxonomy-dialog").showModal();
}
async function generateTaxonomyDiscovery() {
  const button = $("#discover-taxonomy"),
    status = $("#taxonomy-discovery-status");
  button.disabled = true;
  status.textContent = "Agrupando los temas localmente…";
  try {
    const result = await api("/api/taxonomy/discovery", { method: "POST" });
    renderTaxonomyDiscovery(result);
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}
async function saveTaxonomyDiscovery(event) {
  event.preventDefault();
  const button = $("#apply-taxonomy"),
    error = $("#taxonomy-error");
  error.textContent = "";
  const categories = state.taxonomyDiscovery.candidates.map((candidate) => ({
    id: candidate.id,
    enabled: $(`[data-taxonomy-enabled="${candidate.id}"]`).checked,
    name: $(`[data-taxonomy-name="${candidate.id}"]`).value,
    description: $(`[data-taxonomy-description="${candidate.id}"]`).value,
  }));
  button.disabled = true;
  try {
    await api("/api/taxonomy/discovery/apply", {
      method: "POST",
      body: JSON.stringify({ categories }),
    });
    cache.clear();
    state.taxonomy = await api("/api/taxonomy");
    renderFilters();
    await reloadViews(null);
    $("#taxonomy-dialog").close();
    $("#taxonomy-button").classList.add("hidden");
    toast("Categorías personalizadas activadas");
    scheduleSearch(10);
  } catch (problem) {
    error.textContent = problem.message;
  } finally {
    button.disabled = false;
  }
}
$("#taxonomy-button").addEventListener("click", openTaxonomyDiscovery);
$("#close-taxonomy").addEventListener("click", () =>
  $("#taxonomy-dialog").close(),
);
$("#discover-taxonomy").addEventListener("click", generateTaxonomyDiscovery);
$("#taxonomy-discovery-form").addEventListener("submit", saveTaxonomyDiscovery);
async function loadExtensionPanel() {
  const [pkg, devices] = await Promise.all([
    api("/api/v1/xarchive/extension"),
    api("/api/v1/xarchive/devices"),
  ]);
  connectorDevices = devices;
  serverEnrichment = devices.enrichment || null;
  $("#extension-package").innerHTML =
    `<div class="extension-package-meta"><div class="extension-version"><span>Versión</span><strong>${esc(pkg.version)}</strong></div><a class="primary extension-download" href="${esc(pkg.download_url)}">Descargar extensión</a></div><small class="extension-checksum"><span>SHA-256</span><code>${esc(pkg.sha256)}</code></small>`;
  $("#extension-devices").innerHTML = devices.devices.length
    ? devices.devices
        .map(
          (d) =>
            `<div class="device ${d.revoked_at ? "revoked" : ""}"><div><strong>${esc(d.name)}</strong><small>${d.revoked_at ? "Revocado" : `Último contacto: ${d.last_seen_at ? formatDate(d.last_seen_at) : "nunca"}`} · v${esc(d.extension_version || "desconocida")}</small></div><div class="device-actions">${d.revoked_at ? `<button class="danger" data-delete-device="${esc(d.id)}" data-device-name="${esc(d.name)}">Eliminar</button>` : `<button class="danger" data-revoke="${esc(d.id)}">Revocar</button>`}</div></div>`,
        )
        .join("")
    : `<p class="handle">Todavía no hay dispositivos emparejados.</p>`;
  renderServerSync(devices.latest_sync);
  renderSyncInspection();
  await detectConnector();
  if (!connectorStatus?.paired && !$("#extension-setup").dataset.userToggled)
    $("#extension-setup").open = true;
  $$("[data-revoke]").forEach(
    (button) =>
      (button.onclick = async () => {
        await api(
          `/api/v1/xarchive/devices/${encodeURIComponent(button.dataset.revoke)}`,
          { method: "DELETE" },
        );
        toast("Dispositivo revocado");
        await loadExtensionPanel();
      }),
  );
  $$("[data-delete-device]").forEach(
    (button) =>
      (button.onclick = () =>
        requestDeviceDelete(
          button.dataset.deleteDevice,
          button.dataset.deviceName,
        )),
  );
}
function option(item, key, label, extra = "") {
  const value = item[key],
    checked = state.filters[extra || key]?.includes(String(value));
  return `<label class="check"><input type="checkbox" data-filter="${extra || key}" value="${esc(value)}" ${checked ? "checked" : ""}><span>${label}</span><em>${item.count ?? ""}</em></label>`;
}
function renderFacet(kind, query = "", all = false) {
  const q = query.toLowerCase();
  let root, toggle;
  if (kind === "tags") {
    const items = state.taxonomy.tags.filter((x) =>
      x.name.toLowerCase().includes(q),
    );
    root = $("#tag-filters");
    toggle = $("#toggle-tags");
    root.innerHTML = items
      .filter(
        (x, i) =>
          all || q || i < 12 || state.filters.tags.includes(String(x.id)),
      )
      .map((x) => option(x, "id", esc(x.name), "tags"))
      .join("");
    toggle.textContent =
      !q && items.length > 12
        ? all
          ? "Mostrar menos"
          : `Ver las ${items.length} etiquetas`
        : "";
  } else {
    const items = state.taxonomy.authors.filter((x) =>
      (x.name || x.handle || "").toLowerCase().includes(q),
    );
    root = $("#author-filters");
    toggle = $("#toggle-authors");
    root.innerHTML = items
      .filter(
        (x, i) =>
          all ||
          q ||
          i < 12 ||
          state.filters.authors.includes(String(x.handle)),
      )
      .map((x) =>
        option(
          x,
          "handle",
          `@${esc(x.handle)}${x.name ? ` · ${esc(x.name)}` : ""}`,
          "authors",
        ),
      )
      .join("");
    toggle.textContent =
      !q && items.length > 12
        ? all
          ? "Mostrar menos"
          : `Ver los ${items.length} autores`
        : "";
  }
  root.classList.toggle("expanded", all && !q);
  toggle.setAttribute("aria-expanded", String(all && !q));
  root
    .querySelectorAll("[data-filter]")
    .forEach((x) => x.addEventListener("change", filterChanged));
}
function renderFilters() {
  const cats = state.taxonomy.categories,
    parents = cats.filter((c) => !c.parent_id);
  $("#category-filters").innerHTML = parents
    .map(
      (p) =>
        `<div class="category-group">${option(p, "id", esc(p.name), "categories")}${cats
          .filter((c) => c.parent_id === p.id)
          .map(
            (c) =>
              `<div class="category-child">${option(c, "id", esc(c.name), "categories")}</div>`,
          )
          .join("")}</div>`,
    )
    .join("");
  $("#type-filters").innerHTML = state.taxonomy.content_types
    .map(
      (s) =>
        `<label class="type-choice"><input type="checkbox" data-filter="content_types" value="${s}"><span>${typeLabels[s]}</span></label>`,
    )
    .join("");
  renderFacet("tags");
  renderFacet("authors");
  $$("#category-filters [data-filter],#type-filters [data-filter]").forEach(
    (x) => x.addEventListener("change", filterChanged),
  );
  ["#has-media", "#has-links", "#date-from", "#date-to"].forEach((s) =>
    $(s).addEventListener("change", filterChanged),
  );
  updateFilterUX();
}
function filterChanged() {
  for (const key of ["categories", "tags", "authors", "content_types"])
    state.filters[key] = $$(`input[data-filter="${key}"]:checked`).map(
      (x) => x.value,
    );
  state.page = 1;
  updateFilterUX();
  scheduleSearch(120);
}
function params() {
  const p = new URLSearchParams({
    q: state.query,
    page: state.page,
    page_size: state.pageSize,
  });
  for (const key of ["categories", "tags", "authors", "content_types"])
    if (state.filters[key].length) p.set(key, state.filters[key].join(","));
  if ($("#has-media").checked) p.set("has_media", "true");
  if ($("#has-links").checked) p.set("has_links", "true");
  if ($("#date-from").value) p.set("date_from", $("#date-from").value);
  if ($("#date-to").value) p.set("date_to", $("#date-to").value);
  return p;
}
function scheduleSearch(delay = 450) {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(searchNow, delay);
}
async function searchNow() {
  const generation = ++state.generation;
  textController?.abort();
  semanticController?.abort();
  textController = new AbortController();
  semanticController = new AbortController();
  const p = params();
  $("#search-status").textContent = "Buscando coincidencias exactas…";
  try {
    const exact = await api(
      `/api/search/text?${p}`,
      { signal: textController.signal },
      20000,
    );
    if (generation !== state.generation) return;
    renderResults(exact);
    updateFacetCounts(p, generation);
    $("#search-status").textContent = state.query.trim()
      ? "Resultados FTS5 listos · calculando similitud semántica…"
      : "Orden de guardado de X · FTS5 listo";
    if (state.query.trim().length < 2) return;
    const hybrid = await api(
      `/api/search/hybrid?${p}`,
      { signal: semanticController.signal },
      300000,
    );
    if (generation !== state.generation) return;
    renderResults(hybrid);
    $("#search-status").textContent =
      hybrid.effective_mode === "hybrid"
        ? `Ranking híbrido listo${hybrid.semantic.query_cache_hit ? " · consulta en caché" : ""}`
        : `Semántica no disponible · FTS5 sigue activo: ${hybrid.semantic.error || ""}`;
  } catch (error) {
    if (error.name !== "AbortError") {
      $("#search-status").textContent = `Error: ${error.message}`;
      toast(error.message);
    }
  }
}
function highlight(value) {
  let output = esc(value);
  const tokens = state.query.match(/"[^"]+"|\S+/g) || [];
  for (const raw of tokens.slice(0, 8)) {
    const token = esc(raw.replace(/^"|"$/g, "")).replace(
      /[.*+?^${}()|[\]\\]/g,
      "\\$&",
    );
    if (token.length > 1)
      output = output.replace(
        new RegExp(`(${token})`, `ig`),
        "<mark>$1</mark>",
      );
  }
  return output;
}
function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  return isNaN(d)
    ? esc(value)
    : new Intl.DateTimeFormat(uiLocale(), { dateStyle: "medium" }).format(d);
}
function relocalizeVisibleView() {
  $$("[data-local-date]").forEach(
    (node) => (node.textContent = formatDate(node.dataset.localDate)),
  );
  $$("[data-local-number]").forEach((node) => {
    const value = Number(node.dataset.localNumber);
    if (Number.isFinite(value))
      node.textContent = value.toLocaleString(uiLocale());
  });
}
async function updateFacetCounts(p, generation) {
  try {
    const data = await api(`/api/facets?${p}`, {}, 3000);
    if (generation !== state.generation) return;
    for (const key of ["categories", "tags", "authors", "content_types"]) {
      $$(`[data-filter="${key}"]`).forEach((input) => {
        const count = data[key][input.value] || 0,
          label = input.closest("label"),
          counter = label.querySelector("em");
        if (counter) counter.textContent = count;
        input.disabled = !input.checked && count === 0;
        label.classList.toggle("zero", !input.checked && count === 0);
      });
    }
  } catch {}
}
function resultCard(item, board = false) {
  const renderText = board ? esc : highlight;
  const quote = item.quote
    ? `<div class="quote quote-preview"><small>${item.match_only_in_quote ? "Coincidencia solo en la cita · " : "Cita · "}${esc(item.quote.author?.name || item.quote.author?.handle || "contexto")}</small><div class="tweet-text tweet-preview">${item.quote.text ? renderText(item.quote.text) : "Contexto no disponible en la exportación"}</div></div>`
    : "";
  const chip = (css, label, key, value, title) =>
    board
      ? `<span class="chip ${css}">${label}</span>`
      : `<button class="chip ${css}" data-quick="${key}" data-value="${esc(value)}" title="${title}">${label}</button>`;
  const chips = [
    ...item.categories.map((c) =>
      chip(
        "category",
        esc(c.name),
        "categories",
        c.id,
        `Filtrar por ${esc(c.name)}`,
      ),
    ),
    ...item.tags.map((t) =>
      chip("", esc(t.name), "tags", t.id, `Filtrar por ${esc(t.name)}`),
    ),
    ...item.content_types.map((t) =>
      chip(
        "type",
        typeLabels[t] || esc(t),
        "content_types",
        t,
        "Filtrar por formato",
      ),
    ),
  ].join("");
  const handle = item.author.handle
    ? board
      ? `<span class="handle">@${esc(item.author.handle)}</span>`
      : `<button class="handle author-filter" data-quick="authors" data-value="${esc(item.author.handle)}" title="Filtrar por autor">@${esc(item.author.handle)}</button>`
    : "";
  return `<article class="tweet compact" data-id="${item.tweet_id}" title="Doble clic para expandir"><div class="tweet-top">${item.author.avatar && safeUrl(item.author.avatar) ? `<img class="avatar" loading="lazy" src="${esc(safeUrl(item.author.avatar))}" alt="">` : `<div class="avatar"></div>`}<div><div class="author">${esc(item.author.name || item.author.handle || "Autor no disponible")}</div>${handle}</div><div class="date" data-local-date="${esc(item.created_at || "")}">${formatDate(item.created_at)}</div></div><div class="tweet-text tweet-preview">${item.status === "unavailable" ? "Publicación no disponible en la exportación" : renderText(item.text)}</div>${quote}<div class="chips">${chips}</div><div class="actions"><button data-action="detail">Expandir</button><button data-action="organize">Organizar</button><a href="${esc(item.original_url)}" target="_blank" rel="noopener noreferrer">Abrir en X ↗</a><span class="source">${item.sources.includes("semantic") ? "Semántica" : item.sources.includes("browse") ? "Orden de X" : "FTS5"}${item.match_only_in_quote ? " · cita" : ""}</span></div></article>`;
}
function renderResults(data) {
  state.current = data.results;
  state.total = data.total;
  $("#result-count").textContent =
    `${data.total.toLocaleString(uiLocale())} resultados`;
  $("#apply-mobile").textContent =
    `Ver ${data.total.toLocaleString(uiLocale())} resultados`;
  $("#page-label").textContent = `Página ${state.page}`;
  $("#prev").disabled = state.page <= 1;
  $("#next").disabled = state.page * state.pageSize >= data.total;
  $("#results").innerHTML = data.results.length
    ? data.results.map(resultCard).join("")
    : `<div class="empty">No hay resultados con estos criterios.</div>`;
  bindCards();
}
function bindCards(root = document) {
  [...root.querySelectorAll(".tweet")].forEach((card) => {
    if (card.dataset.bound) return;
    card.dataset.bound = "true";
    const id = card.dataset.id;
    card.addEventListener("dblclick", (event) => {
      if (
        !event.target.closest(
          "button,a,input,select,textarea,label,summary,[role='button']",
        )
      )
        openDetail(id);
    });
    card
      .querySelector('[data-action="detail"]')
      .addEventListener("click", () => openDetail(id));
    card
      .querySelector('[data-action="organize"]')
      .addEventListener("click", () => openOrganizer(id));
    card
      .querySelectorAll("[data-quick]")
      .forEach((button) =>
        button.addEventListener("click", () =>
          quickFilter(button.dataset.quick, button.dataset.value),
        ),
      );
  });
}
function quickFilter(key, value) {
  if (!state.filters[key].includes(value)) state.filters[key].push(value);
  const box = document.querySelector(
    `[data-filter="${key}"][value="${CSS.escape(value)}"]`,
  );
  if (box) box.checked = true;
  state.page = 1;
  updateFilterUX();
  scheduleSearch(10);
  scrollTo({ top: 0, behavior: "smooth" });
}
async function openDetail(id) {
  const item = await api(`/api/bookmarks/${id}`, {}, 10000);
  const urls = item.urls
    .map((u) => safeUrl(u.expanded_url || u.url))
    .filter(Boolean);
  const images = item.media.filter((m) => m.type === "photo" && safeUrl(m.url));
  const labels = [
    ...item.categories.map(
      (c) => `<span class="chip category">${esc(c.name)}</span>`,
    ),
    ...item.tags.map((t) => `<span class="chip">${esc(t.name)}</span>`),
  ].join("");
  $("#detail-content").innerHTML =
    `<div class="reader-head"><div><span class="eyebrow">Publicación completa</span><h2>${esc(item.author.name || item.author.handle || "Publicación")}</h2><div class="handle">${item.author.handle ? "@" + esc(item.author.handle) : ""}${item.created_at ? ` · ${formatDate(item.created_at)}` : ""}</div></div></div><div class="tweet-text reader-text">${highlight(item.text || "Publicación no disponible")}</div>${item.card ? `<div class="quote reader-card"><small>Enlace destacado</small><strong>${esc(item.card.title || "Tarjeta")}</strong><p>${esc(item.card.description || "")}</p>${item.card.url && safeUrl(item.card.url) ? `<a href="${esc(safeUrl(item.card.url))}" target="_blank" rel="noopener noreferrer">Abrir enlace ↗</a>` : ""}</div>` : ""}${item.quote ? `<div class="quote reader-quote"><small>Publicación citada · ${esc(item.quote.author?.name || item.quote.author?.handle || "contexto")}</small><div class="tweet-text">${esc(item.quote.text || "Contexto no disponible")}</div>${item.quote.url ? `<a href="${esc(item.quote.url)}" target="_blank" rel="noopener noreferrer">Abrir cita ↗</a>` : ""}</div>` : ""}${images.length ? `<div class="media reader-media">${images.map((m) => `<a href="${esc(safeUrl(m.url))}" target="_blank" rel="noopener noreferrer"><img loading="lazy" src="${esc(safeUrl(m.url))}" alt="${esc(m.alt_text || "")}"></a>`).join("")}</div>` : ""}${urls.length ? `<div class="urls reader-urls">${urls.map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(u)}</a>`).join("")}</div>` : ""}${labels ? `<div class="chips reader-labels">${labels}</div>` : ""}<div class="reader-actions"><button class="secondary" data-reader-organize>Organizar</button><a class="primary" href="${esc(item.original_url)}" target="_blank" rel="noopener noreferrer">Abrir en X ↗</a></div>`;
  $("#detail").showModal();
  $("#detail-content [data-reader-organize]").onclick = () => {
    $("#detail").close();
    openOrganizer(id);
  };
}
let organizerItem = null,
  organizerPending = {},
  organizerSaveTimer = null,
  organizerSaveChain = Promise.resolve(),
  organizerChanged = false;
const normalized = (value) =>
  String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
function queueOrganizerSave(fields, delay = 250) {
  Object.assign(organizerPending, fields);
  organizerChanged = true;
  $("#organize-save-status").textContent = "Pendiente…";
  $("#organize-save-status").className = "save-status pending";
  clearTimeout(organizerSaveTimer);
  organizerSaveTimer = setTimeout(flushOrganizerSave, delay);
}
function flushOrganizerSave() {
  clearTimeout(organizerSaveTimer);
  organizerSaveTimer = null;
  const tweetId = organizerItem?.tweet_id,
    payload = { ...organizerPending };
  organizerPending = {};
  if (!tweetId || !Object.keys(payload).length) return organizerSaveChain;
  $("#organize-save-status").textContent = "Guardando…";
  $("#organize-save-status").className = "save-status pending";
  organizerSaveChain = organizerSaveChain
    .then(() =>
      api(`/api/bookmarks/${tweetId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    )
    .then(() => {
      cache.clear();
      if (organizerItem?.tweet_id === tweetId) {
        $("#organize-save-status").textContent = "Guardado";
        $("#organize-save-status").className = "save-status saved";
      }
    })
    .catch((error) => {
      if (organizerItem?.tweet_id === tweetId) {
        $("#organize-save-status").textContent = "No se pudo guardar";
        $("#organize-save-status").className = "save-status error";
      }
      toast(error.message);
    });
  return organizerSaveChain;
}
function categoryGroup(parent) {
  const children = state.taxonomy.categories.filter(
      (category) => category.parent_id === parent.id,
    ),
    group = [parent, ...children],
    selected = group.filter((category) =>
      organizerItem.categories.some((value) => value.id === category.id),
    ).length;
  const rows = group
    .map(
      (category, index) =>
        `<label class="organize-category-row" data-category-name="${esc(normalized(category.name))}"><input type="checkbox" data-organize-category="${category.id}" ${organizerItem.categories.some((value) => value.id === category.id) ? "checked" : ""}><span>${index === 0 ? "General · " : ""}${esc(category.name)}</span></label>`,
    )
    .join("");
  return `<details class="organize-category-group" data-category-group ${selected ? "open" : ""}><summary><span>${esc(parent.name)}</span>${selected ? `<b>${selected}</b>` : ""}</summary><div>${rows}</div></details>`;
}
function renderOrganizerSelections() {
  const categories = $("#organize-selected-categories"),
    tags = $("#organize-selected-tags");
  if (!categories || !tags) return;
  categories.innerHTML = organizerItem.categories.length
    ? organizerItem.categories
        .map(
          (category) =>
            `<button type="button" class="selection-chip category" data-remove-category="${category.id}">${esc(category.name)} <span>×</span></button>`,
        )
        .join("")
    : '<span class="selection-empty">Ninguna categoría seleccionada</span>';
  tags.innerHTML = organizerItem.tags.length
    ? organizerItem.tags
        .map(
          (tag) =>
            `<button type="button" class="selection-chip" data-remove-tag="${esc(tag.name)}">${esc(tag.name)} <span>×</span></button>`,
        )
        .join("")
    : '<span class="selection-empty">Sin etiquetas</span>';
  $$("[data-remove-category]").forEach(
    (button) =>
      (button.onclick = () => {
        const id = Number(button.dataset.removeCategory);
        organizerItem.categories = organizerItem.categories.filter(
          (category) => category.id !== id,
        );
        const checkbox = document.querySelector(
          `[data-organize-category="${id}"]`,
        );
        if (checkbox) checkbox.checked = false;
        renderOrganizerSelections();
        queueOrganizerSave({
          category_ids: organizerItem.categories.map((category) => category.id),
        });
      }),
  );
  $$("[data-remove-tag]").forEach(
    (button) =>
      (button.onclick = () => {
        organizerItem.tags = organizerItem.tags.filter(
          (tag) => tag.name !== button.dataset.removeTag,
        );
        renderOrganizerSelections();
        queueOrganizerSave({
          tag_names: organizerItem.tags.map((tag) => tag.name),
        });
      }),
  );
}
function addOrganizerTag() {
  const input = $("#organize-tag-input"),
    name = input.value.trim().replace(/^#+/, "");
  if (!name) return;
  if (
    !organizerItem.tags.some((tag) => normalized(tag.name) === normalized(name))
  )
    organizerItem.tags.push(
      state.taxonomy.tags.find(
        (tag) => normalized(tag.name) === normalized(name),
      ) || { name },
    );
  input.value = "";
  renderOrganizerSelections();
  queueOrganizerSave({ tag_names: organizerItem.tags.map((tag) => tag.name) });
}
function renderOrganizer() {
  const parents = state.taxonomy.categories.filter(
    (category) => !category.parent_id,
  );
  $("#organize-title").textContent = "Organizar publicación";
  $("#organize-author").textContent =
    `${organizerItem.author.handle ? "@" + organizerItem.author.handle : organizerItem.author.name || ""} · ${formatDate(organizerItem.created_at)}`;
  $("#organize-save-status").textContent = "Guardado";
  $("#organize-save-status").className = "save-status saved";
  $("#organize-content").innerHTML =
    `<section class="organize-section"><div class="organize-section-head"><div><span class="eyebrow">Clasificación múltiple</span><h3>Categorías</h3></div><span>${state.taxonomy.categories.length} disponibles</span></div><div id="organize-selected-categories" class="selection-list"></div><label class="organize-search"><span>⌕</span><input id="organize-category-search" type="search" placeholder="Buscar una categoría…" aria-label="Buscar una categoría"></label><div class="organize-category-browser">${parents.map(categoryGroup).join("")}</div></section><section class="organize-section"><div class="organize-section-head"><div><span class="eyebrow">Conceptos concretos</span><h3>Etiquetas</h3></div></div><div id="organize-selected-tags" class="selection-list"></div><div class="tag-composer"><input id="organize-tag-input" list="organize-tag-options" placeholder="Buscar o crear etiqueta…"><datalist id="organize-tag-options">${state.taxonomy.tags.map((tag) => `<option value="${esc(tag.name)}"></option>`).join("")}</datalist><button id="organize-add-tag" type="button" class="secondary">Añadir</button></div></section><section class="organize-section"><label class="organize-field">Notas privadas<textarea id="organize-notes" rows="5" placeholder="Añade contexto para ti…">${esc(organizerItem.annotation.notes || "")}</textarea></label></section>`;
  renderOrganizerSelections();
  $$("[data-organize-category]").forEach(
    (input) =>
      (input.onchange = () => {
        const id = Number(input.dataset.organizeCategory),
          category = state.taxonomy.categories.find((value) => value.id === id);
        if (
          input.checked &&
          !organizerItem.categories.some((value) => value.id === id)
        )
          organizerItem.categories.push(category);
        if (!input.checked)
          organizerItem.categories = organizerItem.categories.filter(
            (value) => value.id !== id,
          );
        renderOrganizerSelections();
        queueOrganizerSave({
          category_ids: organizerItem.categories.map((value) => value.id),
        });
      }),
  );
  $("#organize-category-search").oninput = (event) => {
    const query = normalized(event.target.value);
    $$("[data-category-group]").forEach((group) => {
      const rows = [...group.querySelectorAll("[data-category-name]")],
        matches = rows.filter(
          (row) => !query || row.dataset.categoryName.includes(query),
        );
      rows.forEach(
        (row) => (row.hidden = Boolean(query) && !matches.includes(row)),
      );
      group.hidden = !matches.length;
      if (query && matches.length && group.tagName === "DETAILS")
        group.open = true;
    });
  };
  $("#organize-add-tag").onclick = addOrganizerTag;
  $("#organize-tag-input").onkeydown = (event) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      addOrganizerTag();
    }
  };
  $("#organize-notes").oninput = (event) => {
    organizerItem.annotation.notes = event.target.value;
    queueOrganizerSave({ notes: event.target.value }, 650);
  };
}
async function openOrganizer(id) {
  await flushOrganizerSave();
  await organizerSaveChain;
  organizerPending = {};
  organizerChanged = false;
  organizerItem = await api(`/api/bookmarks/${id}`, {}, 10000);
  renderOrganizer();
  $("#organize").showModal();
}
const defaultColumnWidth = 360,
  columnState = new Map();
let draggedColumn = null,
  columnObserver = null;
function activeView() {
  return state.views.find((view) => view.id === state.activeViewId) || null;
}
function setViewStatus(message, kind = "saved") {
  const status = $("#view-save-status");
  status.textContent = message;
  status.className = `save-status ${kind}`;
}
function renderViewsNavigation() {
  if (!state.views.some((view) => view.id === state.activeViewId))
    state.activeViewId =
      (state.views.find((view) => view.is_default) || state.views[0])?.id ||
      null;
  const selector = $("#view-selector"),
    view = activeView(),
    options = state.views
      .map(
        (item) =>
          `<option value="${item.id}" ${item.id === state.activeViewId ? "selected" : ""}>${esc(item.name)}${item.is_default ? " ★" : ""}</option>`,
      )
      .join(""),
    defaultButton = $("#default-view");
  selector.disabled = false;
  selector.innerHTML = state.views.length
    ? `${options}<option disabled>──────────</option><option value="__new__">＋ Nueva vista</option>`
    : '<option value="" selected disabled>Sin vistas guardadas</option><option value="__new__">＋ Nueva vista</option>';
  $("#view-quick-actions").classList.toggle("hidden", !view);
  $("#views-empty").classList.toggle("hidden", Boolean(view));
  $("#view-board").classList.toggle("hidden", !view);
  defaultButton.textContent = view?.is_default ? "★" : "☆";
  defaultButton.classList.toggle("active", Boolean(view?.is_default));
  defaultButton.setAttribute("aria-pressed", String(Boolean(view?.is_default)));
  defaultButton.setAttribute(
    "aria-label",
    view?.is_default ? "Vista de inicio" : "Usar como vista de inicio",
  );
  defaultButton.dataset.tooltip = view?.is_default
    ? "Esta es la vista de inicio"
    : "Usar como vista de inicio";
}
async function reloadViews(selectedId = state.activeViewId) {
  const payload = await api("/api/views");
  state.views = payload.views;
  state.activeViewId = state.views.some((view) => view.id === selectedId)
    ? selectedId
    : (state.views.find((view) => view.is_default) || state.views[0])?.id ||
      null;
  renderViewsNavigation();
  if (state.mode === "views") renderActiveView();
}
function switchWorkspace(mode, viewId = null) {
  state.mode = mode;
  if (viewId !== null) state.activeViewId = Number(viewId);
  $("#timeline-workspace").classList.toggle("hidden", mode !== "timeline");
  $("#views-workspace").classList.toggle("hidden", mode !== "views");
  $("#timeline-mode").classList.toggle("active", mode === "timeline");
  $("#views-mode").classList.toggle("active", mode === "views");
  $("#timeline-mode").setAttribute("aria-pressed", String(mode === "timeline"));
  $("#views-mode").setAttribute("aria-pressed", String(mode === "views"));
  $("#menu").classList.toggle("hidden", mode === "views");
  filtersOpen(false);
  if (mode === "views") {
    renderViewsNavigation();
    renderActiveView();
  }
}
function columnMarkup(column, index, total) {
  const width = Math.max(
    300,
    Math.min(2400, Number(column.width) || defaultColumnWidth),
  );
  return `<section class="view-column" data-column-id="${column.id}" style="--column-width:${width}px" aria-label="Columna ${esc(column.title)}"><header class="view-column-head"><button class="column-drag" draggable="true" aria-label="Arrastrar ${esc(column.title)}" title="Arrastrar columna">⠿</button><div><h2>${esc(column.title)}</h2><span>${esc(column.category_name)}</span></div><b data-column-count data-local-number="${Number(column.count)}">${Number(column.count).toLocaleString(uiLocale())}</b><button class="column-refresh" data-refresh-column="${column.id}" aria-label="Refrescar ${esc(column.title)}" title="Refrescar columna">↻</button><details class="column-menu"><summary aria-label="Opciones de columna"></summary><div><button data-edit-column="${column.id}">Editar columna</button><button data-move-column="-1" ${index === 0 ? "disabled" : ""}>Mover a la izquierda</button><button data-move-column="1" ${index === total - 1 ? "disabled" : ""}>Mover a la derecha</button><button class="danger-link" data-remove-column="${column.id}">Eliminar columna</button></div></details></header><div class="column-results" data-column-results><div class="column-loading">Cargando publicaciones…</div></div><button class="column-more hidden" data-column-more="${column.id}">Cargar más</button><div class="column-resize-handle" data-resize-column="${column.id}" role="separator" aria-label="Cambiar ancho de ${esc(column.title)}. Doble clic para restablecer" aria-orientation="vertical" aria-valuemin="300" aria-valuemax="2400" aria-valuenow="${width}" title="Arrastra para cambiar el ancho · doble clic para restablecer" tabindex="0"></div></section>`;
}
function addColumnCard() {
  return `<button class="add-column-card" data-add-column-card aria-label="Añadir una columna"><span aria-hidden="true">＋</span><strong>Añadir columna</strong><small>Elige una categoría para este espacio</small></button>`;
}
function renderActiveView() {
  const view = activeView(),
    board = $("#view-board");
  columnState.clear();
  columnObserver?.disconnect();
  columnObserver = null;
  if (!view) {
    board.innerHTML = "";
    renderViewsNavigation();
    return;
  }
  const used = new Set(view.columns.map((column) => column.category_id)),
    canAdd =
      !used.has(null) ||
      state.taxonomy.categories.some((category) => !used.has(category.id));
  board.innerHTML =
    view.columns
      .map((column, index) => columnMarkup(column, index, view.columns.length))
      .join("") + (canAdd ? addColumnCard() : "");
  bindBoardControls();
  if ("IntersectionObserver" in window) {
    columnObserver = new IntersectionObserver(
      (entries) => {
        for (const entry of entries)
          if (entry.isIntersecting) {
            const id = Number(entry.target.dataset.columnId);
            columnObserver.unobserve(entry.target);
            loadColumn(id, 1, false);
          }
      },
      { root: board, rootMargin: "0px 320px" },
    );
    board
      .querySelectorAll("[data-column-id]")
      .forEach((column) => columnObserver.observe(column));
  } else for (const column of view.columns) loadColumn(column.id, 1, false);
}
async function loadColumn(columnId, page = 1, append = false) {
  const view = activeView(),
    column = view?.columns.find((item) => item.id === columnId),
    viewId = view?.id;
  if (!column) return false;
  const root = document.querySelector(`[data-column-id="${columnId}"]`),
    results = root?.querySelector("[data-column-results]"),
    more = root?.querySelector("[data-column-more]");
  if (!root || !results) return false;
  const previous = columnState.get(columnId) || {
    page: 0,
    total: 0,
    loading: false,
  };
  if (previous.loading) return false;
  columnState.set(columnId, { ...previous, loading: true });
  if (!append)
    results.innerHTML =
      '<div class="column-loading">Cargando publicaciones…</div>';
  if (more) more.disabled = true;
  try {
    const category =
        column.category_id === null ? "" : `&categories=${column.category_id}`,
      response = await api(
        `/api/search/text?q=&page=${page}&page_size=20${category}`,
      );
    if (state.activeViewId !== viewId || !document.body.contains(root))
      return false;
    if (!append) results.innerHTML = "";
    results.insertAdjacentHTML(
      "beforeend",
      response.results.length
        ? response.results.map((item) => resultCard(item, true)).join("")
        : '<div class="column-empty">No hay publicaciones en esta columna.</div>',
    );
    bindCards(results);
    columnState.set(columnId, { page, total: response.total, loading: false });
    const countNode = root.querySelector("[data-column-count]");
    countNode.dataset.localNumber = String(response.total);
    countNode.textContent = response.total.toLocaleString(uiLocale());
    if (more) {
      more.classList.toggle("hidden", page * 20 >= response.total);
      more.disabled = false;
    }
    return true;
  } catch (error) {
    columnState.set(columnId, { ...previous, loading: false });
    if (!append) {
      results.innerHTML = `<div class="column-error"><span>${esc(error.message)}</span><button class="secondary" data-retry-column="${columnId}">Reintentar</button></div>`;
      results.querySelector("[data-retry-column]").onclick = () =>
        refreshColumn(columnId);
    }
    if (more) more.disabled = false;
    return false;
  }
}
async function refreshColumn(columnId, silent = false) {
  const button = document.querySelector(`[data-refresh-column="${columnId}"]`);
  if (button) {
    button.disabled = true;
    button.classList.add("loading");
  }
  columnState.delete(columnId);
  const ok = await loadColumn(columnId, 1, false);
  if (button) {
    button.disabled = false;
    button.classList.remove("loading");
  }
  if (!silent)
    toast(ok ? "Columna actualizada" : "No se pudo actualizar la columna");
  return ok;
}
async function refreshAllColumns() {
  const view = activeView(),
    button = $("#refresh-view");
  if (!view || button.disabled) return;
  button.disabled = true;
  button.classList.add("loading");
  columnObserver?.disconnect();
  columnObserver = null;
  let failures = 0;
  try {
    for (const column of view.columns) {
      const root = document.querySelector(`[data-column-id="${column.id}"]`),
        results = root?.querySelector("[data-column-results]");
      if (results)
        results.innerHTML =
          '<div class="column-loading">Esperando actualización…</div>';
      columnState.delete(column.id);
    }
    for (const column of view.columns)
      if (!(await refreshColumn(column.id, true))) failures++;
    toast(
      failures
        ? `${failures} ${failures === 1 ? "columna no se pudo actualizar" : "columnas no se pudieron actualizar"}`
        : "Todas las columnas están actualizadas",
    );
  } finally {
    button.disabled = false;
    button.classList.remove("loading");
  }
}
async function saveColumnWidth(columnId, width) {
  const view = activeView(),
    column = view?.columns.find((item) => item.id === columnId);
  if (!view || !column) return;
  column.width = width;
  setViewStatus("Guardando…", "pending");
  try {
    const updated = await api(`/api/views/${view.id}/columns/${columnId}`, {
      method: "PATCH",
      body: JSON.stringify({ width }),
    });
    state.views = state.views.map((item) =>
      item.id === updated.id ? updated : item,
    );
    renderViewsNavigation();
    setViewStatus("Guardado");
  } catch (error) {
    setViewStatus("No se pudo guardar", "error");
    toast(error.message);
    await reloadViews(view.id);
  }
}
function bindColumnResizing(board) {
  board.querySelectorAll("[data-resize-column]").forEach((handle) => {
    const column = handle.closest(".view-column"),
      columnId = Number(handle.dataset.resizeColumn),
      limit = () => Math.min(2400, Math.max(300, board.clientWidth - 4)),
      applyWidth = (width) => {
        column.style.setProperty("--column-width", `${width}px`);
        handle.setAttribute("aria-valuenow", String(width));
      };
    handle.onpointerdown = (event) => {
      if (matchMedia("(max-width: 620px)").matches) return;
      event.preventDefault();
      event.stopPropagation();
      const startX = event.clientX,
        startWidth = column.getBoundingClientRect().width,
        pointerId = event.pointerId;
      let moved = false;
      column.classList.add("resizing");
      handle.setPointerCapture(pointerId);
      handle.onpointermove = (move) => {
        const width = Math.round(
          Math.max(300, Math.min(limit(), startWidth + move.clientX - startX)),
        );
        moved = moved || Math.abs(move.clientX - startX) > 1;
        applyWidth(width);
      };
      handle.onpointerup = handle.onpointercancel = () => {
        const width = Number(handle.getAttribute("aria-valuenow"));
        column.classList.remove("resizing");
        if (handle.hasPointerCapture(pointerId))
          handle.releasePointerCapture(pointerId);
        handle.onpointermove =
          handle.onpointerup =
          handle.onpointercancel =
            null;
        if (moved) saveColumnWidth(columnId, width);
      };
    };
    handle.ondblclick = (event) => {
      if (matchMedia("(max-width: 620px)").matches) return;
      event.preventDefault();
      event.stopPropagation();
      applyWidth(defaultColumnWidth);
      saveColumnWidth(columnId, defaultColumnWidth);
      toast("Ancho de columna restablecido");
    };
    handle.onkeydown = (event) => {
      if (event.key === "Home") {
        event.preventDefault();
        applyWidth(defaultColumnWidth);
        saveColumnWidth(columnId, defaultColumnWidth);
        toast("Ancho de columna restablecido");
        return;
      }
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const current = Number(handle.getAttribute("aria-valuenow")),
        width = Math.max(
          300,
          Math.min(limit(), current + (event.key === "ArrowRight" ? 40 : -40)),
        );
      applyWidth(width);
      saveColumnWidth(columnId, width);
    };
  });
}
function bindBoardControls() {
  const board = $("#view-board");
  bindColumnResizing(board);
  board
    .querySelector("[data-add-column-card]")
    ?.addEventListener("click", () => openColumnEditor());
  board
    .querySelectorAll("[data-edit-column]")
    .forEach(
      (button) =>
        (button.onclick = () =>
          openColumnEditor(Number(button.dataset.editColumn))),
    );
  board
    .querySelectorAll("[data-remove-column]")
    .forEach(
      (button) =>
        (button.onclick = () =>
          requestColumnDelete(Number(button.dataset.removeColumn))),
    );
  board
    .querySelectorAll("[data-refresh-column]")
    .forEach(
      (button) =>
        (button.onclick = () =>
          refreshColumn(Number(button.dataset.refreshColumn))),
    );
  board
    .querySelectorAll("[data-move-column]")
    .forEach(
      (button) =>
        (button.onclick = () =>
          moveColumn(
            Number(button.closest("[data-column-id]").dataset.columnId),
            Number(button.dataset.moveColumn),
          )),
    );
  board.querySelectorAll("[data-column-more]").forEach(
    (button) =>
      (button.onclick = () => {
        const id = Number(button.dataset.columnMore),
          current = columnState.get(id);
        loadColumn(id, (current?.page || 1) + 1, true);
      }),
  );
  board.querySelectorAll(".column-drag").forEach((handle) => {
    handle.addEventListener("dragstart", (event) => {
      draggedColumn = handle.closest(".view-column");
      draggedColumn.classList.add("dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", draggedColumn.dataset.columnId);
    });
    handle.addEventListener("dragend", () => {
      draggedColumn?.classList.remove("dragging");
      draggedColumn = null;
      saveColumnOrder();
    });
  });
  board.ondragover = (event) => {
    if (!draggedColumn) return;
    event.preventDefault();
    const addCard = event.target.closest("[data-add-column-card]"),
      target = event.target.closest(".view-column");
    if (addCard) {
      board.insertBefore(draggedColumn, addCard);
      syncColumnMoveButtons();
      return;
    }
    if (!target || target === draggedColumn) return;
    const box = target.getBoundingClientRect(),
      before = event.clientX < box.left + box.width / 2;
    board.insertBefore(draggedColumn, before ? target : target.nextSibling);
    syncColumnMoveButtons();
  };
  board.ondrop = (event) => event.preventDefault();
}
function syncColumnMoveButtons() {
  const columns = [...$("#view-board").querySelectorAll("[data-column-id]")];
  columns.forEach((column, index) => {
    const buttons = column.querySelectorAll("[data-move-column]");
    if (buttons[0]) buttons[0].disabled = index === 0;
    if (buttons[1]) buttons[1].disabled = index === columns.length - 1;
  });
}
async function saveColumnOrder() {
  const view = activeView();
  if (!view) return;
  const ids = [...$("#view-board").querySelectorAll("[data-column-id]")].map(
    (column) => Number(column.dataset.columnId),
  );
  if (ids.join(",") === view.columns.map((column) => column.id).join(","))
    return;
  setViewStatus("Guardando…", "pending");
  try {
    const updated = await api(`/api/views/${view.id}/columns/order`, {
      method: "PUT",
      body: JSON.stringify({ column_ids: ids }),
    });
    state.views = state.views.map((item) =>
      item.id === updated.id ? updated : item,
    );
    renderViewsNavigation();
    setViewStatus("Guardado");
  } catch (error) {
    setViewStatus("No se pudo guardar", "error");
    toast(error.message);
    await reloadViews(view.id);
  }
}
function moveColumn(columnId, direction) {
  const column = document.querySelector(`[data-column-id="${columnId}"]`),
    sibling =
      direction < 0
        ? column?.previousElementSibling
        : column?.nextElementSibling;
  if (!column || !sibling || !sibling.matches("[data-column-id]")) return;
  if (direction < 0) column.parentElement.insertBefore(column, sibling);
  else column.parentElement.insertBefore(sibling, column);
  syncColumnMoveButtons();
  saveColumnOrder();
}
function renderViewCategoryOptions(selected = []) {
  const chosen = new Set(selected.map(Number)),
    categories = state.taxonomy.categories,
    parents = categories.filter((category) => !category.parent_id);
  $("#view-category-options").innerHTML =
    `<div class="config-category-group"><strong>Timeline</strong><label data-config-category-name="todo timeline general all"><input type="checkbox" value="__all__"><span>Todo · timeline general</span></label></div>` +
    parents.map(
      (parent) =>
        `<div class="config-category-group"><strong>${esc(parent.name)}</strong>${[parent, ...categories.filter((category) => category.parent_id === parent.id)].map((category, index) => `<label data-config-category-name="${esc(normalized(category.name))}"><input type="checkbox" value="${category.id}" ${chosen.has(category.id) ? "checked" : ""}><span>${index === 0 ? "General · " : ""}${esc(category.name)}</span><em>${Number(category.count || 0).toLocaleString(uiLocale())}</em></label>`).join("")}</div>`,
    )
    .join("");
}
function openViewEditor(mode = "create") {
  const view = activeView();
  state.viewEditorMode = mode;
  $("#view-editor-error").textContent = "";
  $("#view-category-search").value = "";
  const create = mode === "create";
  $("#view-category-section").classList.toggle("hidden", !create);
  $("#view-editor-title").textContent = create
    ? "Nueva vista"
    : mode === "rename"
      ? "Renombrar vista"
      : "Duplicar vista";
  $("#save-view-editor").textContent = create
    ? "Crear vista"
    : mode === "rename"
      ? "Guardar nombre"
      : "Crear copia";
  $("#view-name").value = create
    ? ""
    : mode === "rename"
      ? view?.name || ""
      : `${view?.name || "Vista"} · copia`;
  if (create) renderViewCategoryOptions();
  $("#view-editor-dialog").showModal();
  requestAnimationFrame(() => $("#view-name").focus());
}
async function saveViewEditor(event) {
  event.preventDefault();
  const button = $("#save-view-editor"),
    error = $("#view-editor-error"),
    name = $("#view-name").value.trim(),
    view = activeView();
  error.textContent = "";
  if (!name) {
    error.textContent = "Escribe un nombre para la vista.";
    return;
  }
  button.disabled = true;
  try {
    let updated;
    if (state.viewEditorMode === "create") {
      const selectedInputs = [
        ...$("#view-category-options").querySelectorAll("input:checked"),
      ];
      if (!selectedInputs.length) {
        error.textContent =
          "Selecciona al menos una columna para crear la vista.";
        return;
      }
      const includeAll = selectedInputs.some(
          (input) => input.value === "__all__",
        ),
        selected = selectedInputs
          .filter((input) => input.value !== "__all__")
          .map((input) => Number(input.value));
      updated = await api("/api/views", {
        method: "POST",
        body: JSON.stringify({
          name,
          category_ids: selected,
          include_all: includeAll,
        }),
      });
    } else if (state.viewEditorMode === "rename")
      updated = await api(`/api/views/${view.id}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      });
    else
      updated = await api(`/api/views/${view.id}/duplicate`, {
        method: "POST",
        body: JSON.stringify({ name }),
      });
    $("#view-editor-dialog").close();
    await reloadViews(updated.id);
    switchWorkspace("views", updated.id);
    toast(
      state.viewEditorMode === "rename" ? "Vista renombrada" : "Vista guardada",
    );
  } catch (problem) {
    error.textContent = problem.message;
  } finally {
    button.disabled = false;
  }
}
function categorySelectOptions(currentColumn = null) {
  const used = new Set(
      (activeView()?.columns || [])
        .filter((column) => column.id !== currentColumn?.id)
        .map((column) => column.category_id),
    ),
    categories = state.taxonomy.categories,
    parents = categories.filter((category) => !category.parent_id),
    all = `<option value="__all__" ${currentColumn?.category_id === null ? "selected" : ""} ${used.has(null) ? "disabled" : ""}>Todo · timeline general</option>`;
  return (
    all +
    parents
      .map(
        (parent) =>
          `<optgroup label="${esc(parent.name)}">${[
            parent,
            ...categories.filter(
              (category) => category.parent_id === parent.id,
            ),
          ]
            .filter((category) => !used.has(category.id))
            .map(
              (category, index) =>
                `<option value="${category.id}" ${category.id === currentColumn?.category_id ? "selected" : ""}>${index === 0 ? "General · " : ""}${esc(category.name)} (${Number(category.count || 0).toLocaleString(uiLocale())})</option>`,
            )
            .join("")}</optgroup>`,
      )
      .join("")
  );
}
function openColumnEditor(columnId = null) {
  const view = activeView(),
    column = view?.columns.find((item) => item.id === columnId) || null,
    used = new Set((view?.columns || []).map((item) => item.category_id)),
    nothingAvailable =
      used.has(null) &&
      state.taxonomy.categories.every((category) => used.has(category.id));
  if (!column && nothingAvailable) {
    toast("Todas las fuentes ya tienen una columna");
    return;
  }
  state.editingColumnId = column?.id || null;
  $("#column-editor-error").textContent = "";
  $("#column-editor-title").textContent = column
    ? "Editar columna"
    : "Añadir columna";
  $("#save-column-editor").textContent = column
    ? "Guardar columna"
    : "Añadir columna";
  $("#column-category").innerHTML = categorySelectOptions(column);
  $("#column-title").value = column?.custom_title || "";
  $("#column-editor-dialog").showModal();
  requestAnimationFrame(() => $("#column-category").focus());
}
async function saveColumnEditor(event) {
  event.preventDefault();
  const view = activeView(),
    button = $("#save-column-editor"),
    error = $("#column-editor-error"),
    categoryValue = $("#column-category").value,
    payload = {
      category_id: categoryValue === "__all__" ? null : Number(categoryValue),
      title: $("#column-title").value.trim(),
    };
  if (!view) return;
  button.disabled = true;
  error.textContent = "";
  setViewStatus("Guardando…", "pending");
  try {
    const path = state.editingColumnId
        ? `/api/views/${view.id}/columns/${state.editingColumnId}`
        : `/api/views/${view.id}/columns`,
      updated = await api(path, {
        method: state.editingColumnId ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
    state.views = state.views.map((item) =>
      item.id === updated.id ? updated : item,
    );
    $("#column-editor-dialog").close();
    renderViewsNavigation();
    renderActiveView();
    setViewStatus("Guardado");
  } catch (problem) {
    error.textContent = problem.message;
    setViewStatus("No se pudo guardar", "error");
  } finally {
    button.disabled = false;
  }
}
function openDeleteDialog(pending) {
  state.pendingDelete = pending;
  $("#delete-dialog-title").textContent = pending.title;
  $("#delete-dialog-message").textContent = pending.message;
  $("#delete-dialog-preserved").textContent = pending.preserved;
  $("#confirm-delete").textContent = pending.confirmLabel;
  $("#delete-dialog").showModal();
  requestAnimationFrame(() => $("#cancel-delete").focus());
}
function requestColumnDelete(columnId) {
  const view = activeView(),
    column = view?.columns.find((item) => item.id === columnId);
  if (!view || !column) return;
  openDeleteDialog({
    kind: "column",
    viewId: view.id,
    columnId,
    name: column.title,
    title: `¿Eliminar la columna “${column.title}”?`,
    message: "La columna desaparecerá de esta vista personalizada.",
    preserved:
      "La categoría, los tuits y tus cambios de organización se conservarán.",
    confirmLabel: "Eliminar columna",
  });
}
function requestViewDelete() {
  const view = activeView();
  if (!view) return;
  openDeleteDialog({
    kind: "view",
    viewId: view.id,
    name: view.name,
    title: `¿Eliminar la vista “${view.name}”?`,
    message:
      "La disposición de columnas de esta vista se eliminará de todos tus dispositivos.",
    preserved:
      "Los tuits, categorías, etiquetas y otras vistas se conservarán.",
    confirmLabel: "Eliminar vista",
  });
}
function requestDeviceDelete(deviceId, name) {
  openDeleteDialog({
    kind: "device",
    deviceId,
    name,
    title: `¿Eliminar el dispositivo “${name}”?`,
    message:
      "El dispositivo revocado desaparecerá de esta lista y su credencial dejará de almacenarse.",
    preserved:
      "El historial y los resultados de sus sincronizaciones se conservarán.",
    confirmLabel: "Eliminar dispositivo",
  });
}
async function confirmPendingDelete() {
  const pending = state.pendingDelete,
    button = $("#confirm-delete"),
    cancel = $("#cancel-delete");
  if (!pending || button.disabled) return;
  button.disabled = true;
  cancel.disabled = true;
  try {
    if (pending.kind === "column") {
      setViewStatus("Guardando…", "pending");
      const updated = await api(
        `/api/views/${pending.viewId}/columns/${pending.columnId}`,
        { method: "DELETE" },
      );
      state.views = state.views.map((item) =>
        item.id === updated.id ? updated : item,
      );
      $("#delete-dialog").close();
      renderViewsNavigation();
      renderActiveView();
      setViewStatus("Guardado");
      toast("Columna eliminada");
    } else if (pending.kind === "device") {
      await api(
        `/api/v1/xarchive/devices/${encodeURIComponent(pending.deviceId)}/record`,
        { method: "DELETE" },
      );
      $("#delete-dialog").close();
      await loadExtensionPanel();
      toast("Dispositivo eliminado");
    } else {
      await api(`/api/views/${pending.viewId}`, { method: "DELETE" });
      $("#delete-dialog").close();
      await reloadViews(null);
      toast("Vista eliminada");
    }
  } catch (error) {
    if (pending.kind === "column") setViewStatus("No se pudo guardar", "error");
    toast(error.message);
  } finally {
    button.disabled = false;
    cancel.disabled = false;
  }
}
async function makeDefaultView() {
  const view = activeView();
  if (!view) return;
  if (view.is_default) {
    toast("Esta ya es tu vista de inicio");
    return;
  }
  setViewStatus("Guardando…", "pending");
  try {
    await api(`/api/views/${view.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_default: true }),
    });
    await reloadViews(view.id);
    setViewStatus("Guardado");
    toast("Vista de inicio actualizada");
  } catch (error) {
    setViewStatus("No se pudo guardar", "error");
    toast(error.message);
  }
}
$("#timeline-mode").onclick = () => switchWorkspace("timeline");
$("#views-mode").onclick = () => switchWorkspace("views");
$("#view-selector").onchange = (event) => {
  if (event.target.value === "__new__") {
    renderViewsNavigation();
    openViewEditor("create");
    return;
  }
  state.activeViewId = Number(event.target.value);
  renderViewsNavigation();
  renderActiveView();
};
$("#empty-new-view").onclick = () => openViewEditor("create");
$("#rename-view").onclick = () => openViewEditor("rename");
$("#duplicate-view").onclick = () => openViewEditor("duplicate");
$("#default-view").onclick = makeDefaultView;
$("#delete-view").onclick = requestViewDelete;
$("#refresh-view").onclick = refreshAllColumns;
$("#add-column").onclick = () => openColumnEditor();
$("#close-view-editor").onclick = () => $("#view-editor-dialog").close();
$("#close-column-editor").onclick = () => $("#column-editor-dialog").close();
$("#close-delete-dialog").onclick = () => $("#delete-dialog").close();
$("#cancel-delete").onclick = () => $("#delete-dialog").close();
$("#confirm-delete").onclick = confirmPendingDelete;
$("#delete-dialog").addEventListener("close", () => {
  state.pendingDelete = null;
});
$("#view-editor-form").onsubmit = saveViewEditor;
$("#column-editor-form").onsubmit = saveColumnEditor;
$("#view-category-search").oninput = (event) => {
  const query = normalized(event.target.value);
  $$("[data-config-category-name]").forEach(
    (label) =>
      (label.hidden =
        Boolean(query) && !label.dataset.configCategoryName.includes(query)),
  );
  $$(".config-category-group").forEach(
    (group) =>
      (group.hidden = ![
        ...group.querySelectorAll("[data-config-category-name]"),
      ].some((label) => !label.hidden)),
  );
};
function filterLabel(key, value) {
  if (key === "categories")
    return state.taxonomy.categories.find((x) => String(x.id) === value)?.name;
  if (key === "tags")
    return state.taxonomy.tags.find((x) => String(x.id) === value)?.name;
  if (key === "authors") return "@" + value;
  if (key === "content_types") return typeLabels[value];
}
function updateFilterUX() {
  const active = [];
  for (const key of ["categories", "tags", "authors", "content_types"])
    for (const value of state.filters[key])
      active.push({ key, value, label: filterLabel(key, value) });
  if ($("#has-media").checked)
    active.push({ key: "has_media", label: "Con multimedia" });
  if ($("#has-links").checked)
    active.push({ key: "has_links", label: "Con enlaces" });
  if ($("#date-from").value)
    active.push({ key: "date_from", label: `Desde ${$("#date-from").value}` });
  if ($("#date-to").value)
    active.push({ key: "date_to", label: `Hasta ${$("#date-to").value}` });
  $("#active-filters").innerHTML = active
    .map(
      (x) =>
        `<button class="active-filter" data-remove="${x.key}" data-value="${esc(x.value || "")}">${esc(x.label)} <span>×</span></button>`,
    )
    .join("");
  $("#active-filters").classList.toggle("hidden", !active.length);
  $("#filter-summary").textContent = active.length
    ? `${active.length} ${active.length === 1 ? "filtro activo" : "filtros activos"}`
    : "Sin filtros activos";
  $("#clear-filters").disabled = !active.length;
  $("#filter-trigger-count").textContent = active.length;
  $("#filter-trigger-count").classList.toggle("hidden", !active.length);
  for (const [key, id] of [
    ["categories", "#category-selected"],
    ["tags", "#tag-selected"],
    ["authors", "#author-selected"],
    ["content_types", "#type-selected"],
  ]) {
    $(id).textContent = state.filters[key].length;
    $(id).classList.toggle("hidden", !state.filters[key].length);
  }
  $("#more-selected").classList.toggle(
    "hidden",
    !active.some((x) =>
      ["has_media", "has_links", "date_from", "date_to"].includes(x.key),
    ),
  );
  $$("[data-remove]").forEach(
    (b) =>
      (b.onclick = () => {
        const k = b.dataset.remove,
          v = b.dataset.value;
        if (state.filters[k]) {
          state.filters[k] = state.filters[k].filter((x) => x !== v);
          const box = document.querySelector(
            `[data-filter="${k}"][value="${CSS.escape(v)}"]`,
          );
          if (box) box.checked = false;
        } else if (k.startsWith("has_"))
          $("#" + k.replace("_", "-")).checked = false;
        else $("#" + k.replace("_", "-")).value = "";
        filterChanged();
      }),
  );
}
$("#query").addEventListener("input", (e) => {
  state.query = e.target.value;
  state.page = 1;
  scheduleSearch();
});
$("#query").addEventListener("search", () => scheduleSearch(10));
$("#prev").addEventListener("click", () => {
  state.page--;
  searchNow();
  scrollTo(0, 0);
});
$("#next").addEventListener("click", () => {
  state.page++;
  searchNow();
  scrollTo(0, 0);
});
$("#close-detail").addEventListener("click", () => $("#detail").close());
$("#close-organize").addEventListener("click", () => $("#organize").close());
$("#organize").addEventListener("close", () => {
  const changed = organizerChanged;
  organizerChanged = false;
  flushOrganizerSave().then(() => {
    if (changed) {
      scheduleSearch(10);
      if (state.mode === "views") renderActiveView();
    }
  });
});
function closeOnBackdrop(dialog) {
  dialog.addEventListener("click", (event) => {
    const box = dialog.getBoundingClientRect();
    if (
      event.clientX < box.left ||
      event.clientX > box.right ||
      event.clientY < box.top ||
      event.clientY > box.bottom
    )
      dialog.close();
  });
}
function routeModalWheel(dialog) {
  dialog.addEventListener(
    "wheel",
    (event) => {
      if (!dialog.open) return;
      const box = dialog.getBoundingClientRect(),
        inside =
          event.clientX >= box.left &&
          event.clientX <= box.right &&
          event.clientY >= box.top &&
          event.clientY <= box.bottom;
      if (inside) return;
      event.preventDefault();
      const unit =
        event.deltaMode === WheelEvent.DOM_DELTA_LINE
          ? 16
          : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
            ? innerHeight
            : 1;
      window.scrollBy({
        left: event.deltaX * unit,
        top: event.deltaY * unit,
        behavior: "auto",
      });
    },
    { passive: false },
  );
}
closeOnBackdrop($("#detail"));
closeOnBackdrop($("#organize"));
closeOnBackdrop($("#extension-dialog"));
closeOnBackdrop($("#password-dialog"));
closeOnBackdrop($("#view-editor-dialog"));
closeOnBackdrop($("#column-editor-dialog"));
closeOnBackdrop($("#delete-dialog"));
routeModalWheel($("#detail"));
$("#menu").addEventListener("click", () =>
  $("#sidebar").classList.toggle("open"),
);
$("#clear-filters").addEventListener("click", () => {
  $$("[data-filter]").forEach((x) => (x.checked = false));
  $("#has-media").checked = $("#has-links").checked = false;
  $("#date-from").value = $("#date-to").value = "";
  state.filters = { categories: [], tags: [], authors: [], content_types: [] };
  state.page = 1;
  updateFilterUX();
  scheduleSearch(10);
});
function focusSearch() {
  if (state.mode !== "timeline") switchWorkspace("timeline");
  const query = $("#query");
  query.focus({ preventScroll: true });
  query.select();
}
const platform =
    navigator.userAgentData?.platform ||
    navigator.platform ||
    navigator.userAgent ||
    "",
  applePlatform = /Mac|iPhone|iPad|iPod/i.test(platform),
  shortcutName = applePlatform ? "⌘ K" : "Ctrl K";
$("#search-shortcut").textContent = shortcutName;
$("#search-shortcut").setAttribute(
  "aria-label",
  `Enfocar la búsqueda con ${shortcutName}`,
);
window.addEventListener(
  "keydown",
  (event) => {
    const modifier = applePlatform ? event.metaKey : event.ctrlKey;
    if (
      modifier &&
      (event.code === "KeyK" || event.key.toLowerCase() === "k") &&
      !document.querySelector("dialog[open]")
    ) {
      event.preventDefault();
      event.stopPropagation();
      focusSearch();
    }
  },
  { capture: true },
);
$("#search-shortcut").addEventListener("click", focusSearch);
window.xbOnboarding.start({
  api,
  state,
  bootstrap,
  startLibrarySync,
  connectorStatus: () => connectorStatus,
  cache,
  toast,
});
let allTags = false,
  allAuthors = false;
$("#tag-search").addEventListener("input", (e) =>
  renderFacet("tags", e.target.value, allTags),
);
$("#author-search").addEventListener("input", (e) =>
  renderFacet("authors", e.target.value, allAuthors),
);
$("#category-search").addEventListener("input", (e) => {
  $$(".category-group").forEach(
    (x) =>
      (x.hidden = !x.textContent
        .toLowerCase()
        .includes(e.target.value.toLowerCase())),
  );
});
$("#toggle-tags").onclick = () => {
  allTags = !allTags;
  renderFacet("tags", "", allTags);
};
$("#toggle-authors").onclick = () => {
  allAuthors = !allAuthors;
  renderFacet("authors", "", allAuthors);
};
function filtersOpen(open) {
  $("#sidebar").classList.toggle("open", open);
  $("#filter-backdrop").classList.toggle("hidden", !open);
  $("#menu").setAttribute("aria-expanded", open);
  $("#filter-trigger").setAttribute("aria-expanded", open);
}
$("#menu").onclick = () => filtersOpen(true);
$("#filter-trigger").onclick = () => filtersOpen(true);
$("#close-filters").onclick = () => filtersOpen(false);
$("#filter-backdrop").onclick = () => filtersOpen(false);
$("#apply-mobile").onclick = () => filtersOpen(false);
function closeFacets(except = null) {
  $$(".facet").forEach((facet) => {
    if (facet !== except) facet.open = false;
  });
}
$$(".facet").forEach((facet) =>
  facet.querySelector(":scope > summary").addEventListener("click", () => {
    if (!facet.open) closeFacets(facet);
  }),
);
document.addEventListener("pointerdown", (event) => {
  if (!event.target.closest(".facet")) closeFacets();
});

window.addEventListener("xb-language-change", () => {
  setTheme(document.documentElement.dataset.theme);
  setPalette(document.documentElement.dataset.palette);
  if (!state.taxonomy) return;
  renderFilters();
  renderViewsNavigation();
  updateFilterUX();
  if (state.current)
    renderResults({ results: state.current, total: state.total });
  relocalizeVisibleView();
  renderConnectorStatus();
  if (connectorDevices) renderServerSync(connectorDevices.latest_sync);
});
