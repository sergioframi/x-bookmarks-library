(() => {
  const q = (selector) => document.querySelector(selector);
  const root = () => q("#onboarding");
  const content = () => q("#onboarding-content");
  const locale = () => window.xbI18n?.locale() || "es";
  const copy = {
    es: {
      steps: {
        account: "Crear cuenta",
        welcome: "Preferencias",
        extension: "Conectar Chrome",
        import: "Primera importación",
        categories: "Revisar categorías",
        category_confirmation: "Confirmar categorías",
      },
      progress: "Paso {current} de 6",
      eyebrow: "Puesta en marcha local",
      accountTitle: "Crea el usuario de esta biblioteca",
      accountText:
        "Esta instalación es privada y tendrá un único usuario. No hay ninguna cuenta ni contraseña predeterminada.",
      user: "Nombre de usuario",
      password: "Contraseña",
      repeat: "Repetir contraseña",
      create: "Crear usuario",
      passwordHelp: "Usa al menos 12 caracteres.",
      mismatch: "Las contraseñas no coinciden.",
      welcomeTitle: "Hazla realmente tuya",
      welcomeText:
        "Antes de importar, elige el idioma en el que quieres organizar la biblioteca. El tema puede cambiarse en cualquier momento.",
      languageTitle: "Idioma de las categorías",
      spanish: "Español",
      english: "English",
      spanishHelp: "Interfaz y categorías iniciales en español",
      englishHelp: "Interface and initial categories in English",
      warning:
        "Importante: los nombres de las categorías se generarán en este idioma. Son contenido de tu biblioteca y no se traducirán automáticamente si luego cambias el idioma de la interfaz.",
      continue: "Continuar",
      extensionTitle: "Instala y conecta la extensión",
      extensionText:
        "La extensión lee tus guardados usando tu sesión abierta de X en Chrome y los envía directamente a esta Raspberry. No interviene ningún servicio externo.",
      install1: "Descarga y descomprime la extensión.",
      install2:
        "Abre <code>chrome://extensions</code>, activa el modo desarrollador y usa “Cargar descomprimida”.",
      install3:
        "Vuelve aquí, genera un código y pulsa el icono de xarchive para emparejarla.",
      download: "Descargar extensión",
      code: "Generar código",
      checkConnection: "Comprobar conexión",
      noDevice: "Aún no aparece ningún dispositivo conectado.",
      connected: "Extensión conectada. Ya puedes hacer la primera importación.",
      importTitle: "Importa tus guardados por primera vez",
      importText:
        "Abre X en este Chrome con tu cuenta iniciada. La primera revisión recorrerá la colección completa; puede tardar y debe dejarse abierta la pestaña de la extensión.",
      startImport: "Iniciar importación completa",
      importWorking: "Importación en curso…",
      waiting: "Esperando la primera importación…",
      processing:
        "{bookmarks} bookmarks recibidos. Generando embeddings y descubriendo temas localmente…",
      draftReady: "La propuesta de categorías está preparada.",
      activity: "Actividad de la importación",
      requesting: "Solicitando una revisión completa a la extensión…",
      started: "La extensión ha iniciado la importación.",
      received: "La Raspberry ha recibido {bookmarks} bookmarks.",
      preparing: "Generando embeddings y descubriendo temas localmente…",
      proposalReady: "Propuesta de categorías preparada.",
      pages: "páginas",
      extensionError: "La extensión ha informado de un error: {error}",
      alreadyRunning: "Ya hay una sincronización o enriquecimiento en curso.",
      embeddingsProgress: "Embeddings: {completed} de {total} ({percent}%).",
      taxonomyLoading: "Cargando vectores para descubrir temas…",
      taxonomyClustering: "Seleccionando agrupaciones temáticas…",
      taxonomyLabels: "Nombrando categoría {completed} de {total}…",
      taxonomyReady: "Borrador de categorías preparado.",
      retryImport:
        "El procesamiento anterior está detenido. Inicia una nueva importación para continuar desde los embeddings ya guardados.",
      extensionProgress: "Progreso",
      diagnostics: "Diagnóstico",
      activityLog: "Registro de actividad",
      phase: "Fase",
      folders: "Carpetas",
      speed: "Velocidad",
      elapsed: "Tiempo",
      categoriesTitle: "Revisa la propuesta local",
      categoriesText:
        "Puedes desactivar grupos o editar sus nombres y descripciones. El contenido analizado no ha salido de esta instalación.",
      review: "Revisar selección",
      bookmarks: "bookmarks",
      cohesion: "cohesión",
      confirmTitle: "Confirma tu organización",
      confirmText:
        "Este es el nuevo paso final: comprueba el resumen antes de activar la taxonomía. Después podrás corregir categorías manualmente en cada bookmark.",
      back: "Volver y editar",
      activate: "Activar categorías",
      activating: "Activando categorías…",
      activationActivity: "Progreso de activación",
      activatePreparing: "Validando la selección de categorías…",
      activateCreating: "Creando las categorías personalizadas…",
      activateAssigning: "Asignando los bookmarks a sus categorías…",
      activateIndexing: "Actualizando el índice de búsqueda…",
      activateFinishing: "Guardando la configuración final…",
      activateDone: "Categorías activadas correctamente.",
      done: "Tu biblioteca está lista",
      needOne: "Selecciona al menos una categoría.",
      theme: "Cambiar tema",
      language: "Cambiar idioma",
      palette: "Cambiar paleta",
      paletteTitle: "Previsualizar paleta",
      paletteHelp: "Combínala con claro u oscuro",
      paletteNames: {
        mono: ["Monocroma", "Grises limpios y neutros"],
        ice: ["Azul hielo", "Fría, ligera y minimalista"],
        lavender: ["Lavanda nube", "Suave y contemporánea"],
        rose: ["Rosa cuarzo", "Serena y ligeramente cálida"],
        coral: ["Arena y coral", "Luminosa y editorial"],
      },
      syncError:
        "No se pudo iniciar la extensión. Comprueba que está instalada, emparejada y que X está abierto.",
    },
    en: {
      steps: {
        account: "Create account",
        welcome: "Preferences",
        extension: "Connect Chrome",
        import: "First import",
        categories: "Review categories",
        category_confirmation: "Confirm categories",
      },
      progress: "Step {current} of 6",
      eyebrow: "Local setup",
      accountTitle: "Create this library's user",
      accountText:
        "This is a private installation with a single user. There is no default account or password.",
      user: "Username",
      password: "Password",
      repeat: "Repeat password",
      create: "Create user",
      passwordHelp: "Use at least 12 characters.",
      mismatch: "Passwords do not match.",
      welcomeTitle: "Make it truly yours",
      welcomeText:
        "Before importing, choose the language used to organize the library. You can change the theme at any time.",
      languageTitle: "Category language",
      spanish: "Español",
      english: "English",
      spanishHelp: "Interface and initial categories in Spanish",
      englishHelp: "Interface and initial categories in English",
      warning:
        "Important: category names will be generated in this language. They are library content and will not be translated automatically if you later change the interface language.",
      continue: "Continue",
      extensionTitle: "Install and connect the extension",
      extensionText:
        "The extension reads your bookmarks through your active X session in Chrome and sends them directly to this Raspberry Pi. No external service is involved.",
      install1: "Download and unzip the extension.",
      install2:
        "Open <code>chrome://extensions</code>, enable Developer mode and choose “Load unpacked”.",
      install3:
        "Return here, generate a code and click the xarchive icon to pair it.",
      download: "Download extension",
      code: "Generate code",
      checkConnection: "Check connection",
      noDevice: "No connected device is visible yet.",
      connected: "Extension connected. You can now run the first import.",
      importTitle: "Import your bookmarks for the first time",
      importText:
        "Open X in this Chrome profile and sign in. The first full scan can take a while; keep the extension tab open.",
      startImport: "Start full import",
      importWorking: "Import in progress…",
      waiting: "Waiting for the first import…",
      processing:
        "{bookmarks} bookmarks received. Creating embeddings and discovering topics locally…",
      draftReady: "The category proposal is ready.",
      activity: "Import activity",
      requesting: "Requesting a full scan from the extension…",
      started: "The extension started the import.",
      received: "The Raspberry Pi received {bookmarks} bookmarks.",
      preparing: "Creating embeddings and discovering topics locally…",
      proposalReady: "Category proposal ready.",
      pages: "pages",
      extensionError: "The extension reported an error: {error}",
      alreadyRunning: "A synchronization or enrichment job is already running.",
      embeddingsProgress: "Embeddings: {completed} of {total} ({percent}%).",
      taxonomyLoading: "Loading vectors to discover topics…",
      taxonomyClustering: "Selecting topic groups…",
      taxonomyLabels: "Naming category {completed} of {total}…",
      taxonomyReady: "Category draft prepared.",
      retryImport:
        "The previous processing job is stopped. Start a new import to continue from the saved embeddings.",
      extensionProgress: "Progress",
      diagnostics: "Diagnostics",
      activityLog: "Activity log",
      phase: "Phase",
      folders: "Folders",
      speed: "Speed",
      elapsed: "Elapsed",
      categoriesTitle: "Review the local proposal",
      categoriesText:
        "Disable groups or edit their names and descriptions. The analyzed content never left this installation.",
      review: "Review selection",
      bookmarks: "bookmarks",
      cohesion: "cohesion",
      confirmTitle: "Confirm your organization",
      confirmText:
        "This is the new final step: check the summary before activating the taxonomy. You can still correct categories manually on each bookmark later.",
      back: "Back and edit",
      activate: "Activate categories",
      activating: "Activating categories…",
      activationActivity: "Activation progress",
      activatePreparing: "Validating the category selection…",
      activateCreating: "Creating the personalized categories…",
      activateAssigning: "Assigning bookmarks to their categories…",
      activateIndexing: "Updating the search index…",
      activateFinishing: "Saving the final configuration…",
      activateDone: "Categories activated successfully.",
      done: "Your library is ready",
      needOne: "Select at least one category.",
      theme: "Change theme",
      language: "Change language",
      palette: "Change palette",
      paletteTitle: "Preview palette",
      paletteHelp: "Combine it with light or dark mode",
      paletteNames: {
        mono: ["Monochrome", "Clean, neutral grays"],
        ice: ["Ice blue", "Cool, light and minimal"],
        lavender: ["Cloud lavender", "Soft and contemporary"],
        rose: ["Quartz rose", "Calm and slightly warm"],
        coral: ["Sand and coral", "Bright and editorial"],
      },
      syncError:
        "Could not start the extension. Check that it is installed, paired and X is open.",
    },
  };
  let ctx = null;
  let onboarding = null;
  let appBootstrapped = false;
  let pollTimer = null;
  let importLaunchPending = false;
  let activationTimers = [];
  let currentStep = "account";
  let importLog = [];
  const importEvents = new Set();
  const t = (key) => copy[locale()][key];
  const escape = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (character) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[character],
    );
  const stepNumber = (step) =>
    ({
      account: 1,
      welcome: 2,
      extension: 3,
      import: 4,
      categories: 5,
      category_confirmation: 6,
    })[step] || 1;

  function show(step) {
    clearTimeout(pollTimer);
    currentStep = step;
    root().classList.remove("hidden");
    q("#login").classList.add("hidden");
    const number = stepNumber(step);
    q("#onboarding-step-label").textContent =
      `${t("progress").replace("{current}", number)} · ${t("steps")[step] || ""}`;
    q("#onboarding-progress-bar").style.width = `${(number / 6) * 100}%`;
    render(step);
  }

  function toolbar() {
    const dark = document.documentElement.dataset.theme === "dark";
    q("#onboarding-theme-icon").textContent = dark ? "☀" : "☾";
    q("#onboarding-theme").title = t("theme");
    q("#onboarding-palette").title = t("palette");
    q("#onboarding-language").textContent = locale() === "es" ? "EN" : "ES";
    q("#onboarding-language").title = t("language");
    q("#onboarding-palette-title").textContent = t("paletteTitle");
    q("#onboarding-palette-help").textContent = t("paletteHelp");
    const selected = document.documentElement.dataset.palette || "ice";
    document.querySelectorAll("[data-onboarding-palette]").forEach((button) => {
      const value = button.dataset.onboardingPalette,
        active = value === selected,
        labels = t("paletteNames")[value];
      button.classList.toggle("active", active);
      button.setAttribute("aria-checked", String(active));
      q(`[data-onboarding-palette-name="${value}"]`).textContent = labels[0];
      q(`[data-onboarding-palette-help="${value}"]`).textContent = labels[1];
    });
  }

  function render(step) {
    toolbar();
    const templates = {
      account: `<span class="eyebrow">${t("eyebrow")}</span><h1>${t("accountTitle")}</h1><p>${t("accountText")}</p><form id="onboarding-account-form"><label>${t("user")}<input id="setup-user" autocomplete="username" minlength="2" maxlength="100" required autofocus></label><label>${t("password")}<input id="setup-password" type="password" autocomplete="new-password" minlength="12" maxlength="500" required><small>${t("passwordHelp")}</small></label><label>${t("repeat")}<input id="setup-repeat" type="password" autocomplete="new-password" minlength="12" maxlength="500" required></label><p id="onboarding-error" class="error" role="alert"></p><button class="primary" type="submit">${t("create")}</button></form>`,
      welcome: `<span class="eyebrow">${t("eyebrow")}</span><h1>${t("welcomeTitle")}</h1><p>${t("welcomeText")}</p><h2>${t("languageTitle")}</h2><div class="onboarding-choice"><button data-onboarding-locale="es" class="${locale() === "es" ? "active" : ""}"><strong>${t("spanish")}</strong><small>${t("spanishHelp")}</small></button><button data-onboarding-locale="en" class="${locale() === "en" ? "active" : ""}"><strong>${t("english")}</strong><small>${t("englishHelp")}</small></button></div><div class="onboarding-notice">${t("warning")}</div><div class="onboarding-actions"><button class="primary" data-next="extension">${t("continue")}</button></div>`,
      extension: `<span class="eyebrow">${t("eyebrow")}</span><h1>${t("extensionTitle")}</h1><p>${t("extensionText")}</p><ol class="onboarding-install"><li>${t("install1")}</li><li>${t("install2")}</li><li>${t("install3")}</li></ol><div id="onboarding-extension-package" class="onboarding-status">…</div><div class="onboarding-actions"><button class="secondary" id="onboarding-code">${t("code")}</button><a class="primary" id="onboarding-download" href="#">${t("download")}</a></div><div id="onboarding-pairing" class="onboarding-code"></div><p id="onboarding-error" class="error"></p><div class="onboarding-actions"><button class="primary" id="onboarding-check-device">${t("checkConnection")}</button></div>`,
      import: `<span class="eyebrow">${t("eyebrow")}</span><h1>${t("importTitle")}</h1><p>${t("importText")}</p><div id="onboarding-import-status" class="onboarding-status">${t("waiting")}</div><section id="onboarding-extension-progress" class="onboarding-live-progress hidden"><header><strong>${t("extensionProgress")}</strong><span id="onboarding-progress-source"></span></header><div class="onboarding-live-track"><span id="onboarding-live-bar"></span></div><div class="onboarding-live-stats"><div><small>${t("phase")}</small><strong id="onboarding-stat-phase">—</strong></div><div><small>${t("bookmarks")}</small><strong id="onboarding-stat-bookmarks">0</strong></div><div><small>${t("pages")}</small><strong id="onboarding-stat-pages">0</strong></div><div><small>${t("folders")}</small><strong id="onboarding-stat-folders">—</strong></div><div><small>${t("speed")}</small><strong id="onboarding-stat-speed">—</strong></div><div><small>${t("elapsed")}</small><strong id="onboarding-stat-elapsed">0:00</strong></div></div></section><details id="onboarding-extension-diagnostics" class="onboarding-diagnostics"><summary><span>${t("diagnostics")}</span><small>${t("activityLog")}</small></summary><div id="onboarding-diagnostic-summary" class="onboarding-diagnostic-summary"></div><section class="onboarding-import-log"><header><strong>${t("activity")}</strong><span aria-hidden="true">●</span></header><div id="onboarding-import-log" role="log" aria-live="polite"></div></section></details><p id="onboarding-error" class="error"></p><div class="onboarding-actions"><button class="primary" id="onboarding-start-import">${t("startImport")}</button></div>`,
      categories: categoriesTemplate(),
      category_confirmation: confirmationTemplate(),
    };
    content().innerHTML = templates[step] || "";
    bind(step);
    if (step === "import") {
      appendImportLog(t("waiting"), "waiting");
      renderImportLog();
    }
  }

  function candidates() {
    return ctx?.state?.taxonomyDiscovery?.candidates || [];
  }
  function savedChoices() {
    try {
      return (
        JSON.parse(
          localStorage.getItem(
            `xb-taxonomy-${ctx.state.taxonomyDiscovery?.run_id}`,
          ),
        ) || null
      );
    } catch {
      return null;
    }
  }
  function currentChoices() {
    return candidates().map((candidate) => ({
      id: candidate.id,
      enabled: q(`[data-ob-enabled="${candidate.id}"]`)?.checked ?? true,
      name: q(`[data-ob-name="${candidate.id}"]`)?.value ?? candidate.name,
      description:
        q(`[data-ob-description="${candidate.id}"]`)?.value ??
        candidate.description,
    }));
  }
  function categoriesTemplate() {
    const saved = savedChoices();
    const byId = new Map((saved || []).map((item) => [item.id, item]));
    return `<span class="eyebrow">${t("eyebrow")}</span><h1>${t("categoriesTitle")}</h1><p>${t("categoriesText")}</p><div class="onboarding-categories">${candidates()
      .map((candidate) => {
        const choice = byId.get(candidate.id) || candidate;
        return `<article class="onboarding-category"><label class="onboarding-category-head"><input type="checkbox" data-ob-enabled="${candidate.id}" ${choice.enabled === false ? "" : "checked"}><span><strong>${candidate.bookmark_count.toLocaleString(locale())} ${t("bookmarks")}</strong><small>${Number(candidate.cohesion).toLocaleString(locale(), { maximumFractionDigits: 2 })} ${t("cohesion")}</small></span></label><label>${locale() === "en" ? "Name" : "Nombre"}<input data-ob-name="${candidate.id}" maxlength="100" value="${escape(choice.name)}" required></label><label>${locale() === "en" ? "Description" : "Descripción"}<textarea data-ob-description="${candidate.id}" maxlength="500" rows="2">${escape(choice.description)}</textarea></label></article>`;
      })
      .join(
        "",
      )}</div><p id="onboarding-error" class="error"></p><div class="onboarding-actions"><button class="primary" id="onboarding-review">${t("review")}</button></div>`;
  }
  function confirmationTemplate() {
    const selected = (savedChoices() || []).filter((item) => item.enabled);
    return `<span class="eyebrow">${t("eyebrow")}</span><h1>${t("confirmTitle")}</h1><p>${t("confirmText")}</p><ul class="onboarding-summary">${selected.map((item) => `<li><strong>${escape(item.name)}</strong>${item.description ? `<br><small>${escape(item.description)}</small>` : ""}</li>`).join("")}</ul><section id="onboarding-activation-progress" class="onboarding-activation-progress hidden" aria-live="polite"><header><strong>${t("activationActivity")}</strong><span class="onboarding-spinner" aria-hidden="true"></span></header><div id="onboarding-activation-log" role="log"></div></section><p id="onboarding-error" class="error"></p><div class="onboarding-actions"><button class="secondary" id="onboarding-back">${t("back")}</button><button class="primary" id="onboarding-activate">${t("activate")}</button></div>`;
  }

  async function patch(values) {
    onboarding = await ctx.api("/api/onboarding", {
      method: "PATCH",
      body: JSON.stringify(values),
    });
    return onboarding;
  }
  async function move(step) {
    await patch({ step });
    show(step);
    if (step === "extension") loadPackage();
    if (step === "import") pollImport();
  }
  async function ensureApp() {
    if (!appBootstrapped) {
      appBootstrapped = true;
      await ctx.bootstrap(false);
    }
  }

  function bind(step) {
    if (step === "account")
      q("#onboarding-account-form").onsubmit = createAccount;
    q("[data-next]")?.addEventListener("click", (event) =>
      move(event.currentTarget.dataset.next),
    );
    q("#onboarding-code")?.addEventListener("click", createCode);
    q("#onboarding-check-device")?.addEventListener("click", checkDevice);
    q("#onboarding-start-import")?.addEventListener("click", startImport);
    q("#onboarding-review")?.addEventListener("click", reviewCategories);
    q("#onboarding-back")?.addEventListener("click", () => move("categories"));
    q("#onboarding-activate")?.addEventListener("click", activateCategories);
    document
      .querySelectorAll("[data-onboarding-locale]")
      .forEach(
        (button) =>
          (button.onclick = () =>
            chooseLocale(button.dataset.onboardingLocale)),
      );
  }

  async function createAccount(event) {
    event.preventDefault();
    const password = q("#setup-password").value,
      repeat = q("#setup-repeat").value,
      error = q("#onboarding-error"),
      button = event.submitter;
    if (password !== repeat) {
      error.textContent = t("mismatch");
      return;
    }
    button.disabled = true;
    error.textContent = "";
    try {
      const response = await fetch("/api/setup", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: q("#setup-user").value,
          password,
          locale: locale(),
          theme: document.documentElement.dataset.theme || "light",
          palette: document.documentElement.dataset.palette || "ice",
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || response.statusText);
      ctx.state.csrf = data.csrf;
      onboarding = data.onboarding;
      await ensureApp();
      show("welcome");
    } catch (problem) {
      error.textContent = problem.message;
    } finally {
      button.disabled = false;
    }
  }
  async function chooseLocale(value) {
    window.xbI18n.setLocale(value);
    toolbar();
    if (ctx.state.csrf && onboarding?.taxonomy_state === "empty")
      await patch({ locale: value });
    render(currentStep);
  }
  async function loadPackage() {
    try {
      const pkg = await ctx.api("/api/v1/xarchive/extension");
      q("#onboarding-download").href = pkg.download_url;
      q("#onboarding-extension-package").textContent =
        `v${pkg.version} · SHA-256 ${pkg.sha256.slice(0, 16)}…`;
    } catch (problem) {
      q("#onboarding-error").textContent = problem.message;
    }
  }
  async function createCode() {
    try {
      const result = await ctx.api("/api/v1/xarchive/pairing-codes", {
        method: "POST",
      });
      q("#onboarding-pairing").textContent = result.code;
      try {
        await navigator.clipboard.writeText(result.code);
      } catch {}
    } catch (problem) {
      q("#onboarding-error").textContent = problem.message;
    }
  }
  async function checkDevice() {
    const devices = await ctx.api("/api/v1/xarchive/devices");
    if (!devices.devices.some((device) => !device.revoked_at)) {
      q("#onboarding-error").textContent = t("noDevice");
      return;
    }
    q("#onboarding-error").textContent = "";
    await move("import");
  }
  async function startImport() {
    q("#onboarding-error").textContent = "";
    const button = q("#onboarding-start-import"),
      extensionRunning = ctx.connectorStatus?.()?.syncState?.status === "running";
    if (importLaunchPending || extensionRunning || onboarding?.enrichment?.busy) {
      q("#onboarding-error").textContent = t("alreadyRunning");
      return;
    }
    importLaunchPending = true;
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    button.textContent = t("importWorking");
    appendImportLog(t("requesting"));
    try {
      const result = await ctx.startLibrarySync("full");
      if (!result) {
        q("#onboarding-error").textContent = t("syncError");
        importLaunchPending = false;
        button.disabled = false;
        button.removeAttribute("aria-busy");
        button.textContent = t("startImport");
        return;
      }
      appendImportLog(t("started"));
      pollImport();
    } catch {
      q("#onboarding-error").textContent = t("syncError");
      importLaunchPending = false;
      button.disabled = false;
      button.removeAttribute("aria-busy");
      button.textContent = t("startImport");
    }
  }
  function renderImportLog() {
    const box = q("#onboarding-import-log");
    if (!box) return;
    box.innerHTML = importLog
      .map(
        (item) =>
          `<p><time>${escape(item.time)}</time><span>${escape(item.message)}</span></p>`,
      )
      .join("");
    box.scrollTop = box.scrollHeight;
  }
  function appendImportLog(message, key = message, timestamp = null) {
    if (!message || importEvents.has(key)) return;
    importEvents.add(key);
    const date = timestamp
      ? new Date(String(timestamp).includes("T") ? timestamp : `${String(timestamp).replace(" ", "T")}Z`)
      : new Date();
    importLog.push({
      time: date.toLocaleTimeString(locale(), {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
      message,
    });
    if (importLog.length > 30) importLog = importLog.slice(-30);
    renderImportLog();
  }
  function elapsedLabel(seconds) {
    const value = Math.max(0, Number(seconds || 0)),
      minutes = Math.floor(value / 60),
      remainder = Math.floor(value % 60);
    return `${minutes}:${String(remainder).padStart(2, "0")}`;
  }
  function renderLiveProgress(job, enrichment) {
    const section = q("#onboarding-extension-progress");
    if (!section) return;
    const localJob = enrichment.job || {},
      extensionRunning = job.status === "running",
      localRunning = Boolean(enrichment.busy),
      visible = extensionRunning || localRunning || job.status === "completed";
    section.classList.toggle("hidden", !visible);
    if (!visible) return;
    const localTotal = Number(enrichment.documents || localJob.total || 0),
      localCompleted = Number(enrichment.embeddings || localJob.completed || 0),
      localPercent = localTotal
        ? Math.min(100, Math.round((localCompleted * 100) / localTotal))
        : 0,
      bar = q("#onboarding-live-bar");
    bar.classList.toggle("indeterminate", extensionRunning);
    bar.style.width = extensionRunning ? "38%" : `${localPercent}%`;
    q("#onboarding-progress-source").textContent = extensionRunning
      ? "Chrome"
      : localRunning
        ? "Local"
        : "✓";
    q("#onboarding-stat-phase").textContent = extensionRunning
      ? job.phase || "—"
      : localJob.message || job.phase || "—";
    q("#onboarding-stat-bookmarks").textContent = Number(
      job.bookmarks || enrichment.documents || 0,
    ).toLocaleString(locale());
    q("#onboarding-stat-pages").textContent = job.pages || "—";
    q("#onboarding-stat-folders").textContent = job.folders || "—";
    q("#onboarding-stat-speed").textContent = job.speed || "—";
    q("#onboarding-stat-elapsed").textContent = elapsedLabel(
      job.elapsedSeconds,
    );
  }
  function renderConnectorDiagnostics(status) {
    const root = q("#onboarding-diagnostic-summary");
    if (!root) return;
    const diagnostics = status?.diagnostics || {},
      operations = diagnostics.queryOperations || {};
    root.innerHTML = [
      ["Extension", status?.version || "—"],
      ["X account", diagnostics.accountDetected ? "OK" : "—"],
      ["Credentials", diagnostics.credentialsAvailable ? "OK" : "—"],
      ["Bookmarks query", operations.Bookmarks ? "OK" : "—"],
    ]
      .map(
        ([label, value]) =>
          `<span><small>${escape(label)}</small><strong>${escape(value)}</strong></span>`,
      )
      .join("");
  }
  function enrichmentMessage(event) {
    const details = event.details || {};
    if (event.phase === "embeddings") {
      const completed = Number(details.completed || 0),
        total = Number(details.total || 0),
        percent = total ? Math.round((completed * 100) / total) : 0;
      return t("embeddingsProgress")
        .replace("{completed}", completed.toLocaleString(locale()))
        .replace("{total}", total.toLocaleString(locale()))
        .replace("{percent}", percent);
    }
    if (event.phase === "taxonomy_loading") return t("taxonomyLoading");
    if (event.phase === "taxonomy_clustering") return t("taxonomyClustering");
    if (event.phase === "taxonomy_labels")
      return t("taxonomyLabels")
        .replace("{completed}", Number(details.completed || 0))
        .replace("{total}", Number(details.total || 0));
    if (event.phase === "taxonomy_ready") return t("taxonomyReady");
    return event.message;
  }
  async function checkImport() {
    onboarding = await ctx.api("/api/onboarding");
    const box = q("#onboarding-import-status");
    if (!box) return;
    const enrichment = onboarding.enrichment || {},
      localJob = enrichment.job || {},
      button = q("#onboarding-start-import"),
      job = ctx.connectorStatus?.()?.syncState || {};
    const connector = ctx.connectorStatus?.() || {},
      extensionRunning = job.status === "running";
    if (extensionRunning || enrichment.busy) importLaunchPending = false;
    if (job.status === "error" || (job.status === "completed" && !enrichment.busy))
      importLaunchPending = false;
    const busy = importLaunchPending || extensionRunning || Boolean(enrichment.busy);
    if (button) {
      button.disabled = busy;
      button.textContent = busy ? t("importWorking") : t("startImport");
      button.toggleAttribute("aria-busy", busy);
    }
    renderLiveProgress(job, enrichment);
    renderConnectorDiagnostics(connector);
    for (const [index, entry] of (connector.logs || []).entries())
      appendImportLog(
        `Extension · ${entry.message}`,
        `extension:${entry.at}:${index}`,
        entry.at,
      );
    for (const event of enrichment.events || [])
      appendImportLog(
        enrichmentMessage(event),
        `server:${event.id}`,
        event.created_at,
      );
    if (job.status === "running") {
      const detail = [
        job.phase,
        job.bookmarks ? `${job.bookmarks} bookmarks` : "",
        job.pages ? `${job.pages} ${t("pages")}` : "",
      ]
        .filter(Boolean)
        .join(" · ");
      appendImportLog(detail, `running:${detail}`);
    } else if (job.status === "error")
      appendImportLog(
        t("extensionError").replace("{error}", job.error || "—"),
        `error:${job.error}`,
      );
    else if (job.status === "completed")
      appendImportLog(
        job.phase || t("started"),
        `completed:${job.finishedAt || ""}`,
      );
    if (onboarding.taxonomy_state === "draft") {
      box.textContent = t("draftReady");
      appendImportLog(t("proposalReady"), "proposal-ready");
      ctx.state.taxonomyDiscovery = await ctx.api("/api/taxonomy/discovery");
      await move("categories");
      return;
    }
    if (onboarding.bookmarks) {
      const completed = Number(enrichment.embeddings || 0),
        total = Number(enrichment.documents || onboarding.bookmarks || 0),
        percent = total ? Math.round((completed * 100) / total) : 0;
      box.textContent = !enrichment.busy
        ? t("retryImport")
        : String(localJob.phase || "").startsWith("embeddings")
          ? t("embeddingsProgress")
              .replace("{completed}", completed.toLocaleString(locale()))
              .replace("{total}", total.toLocaleString(locale()))
              .replace("{percent}", percent)
          : localJob.message ||
            t("processing").replace(
              "{bookmarks}",
              onboarding.bookmarks.toLocaleString(locale()),
            );
      appendImportLog(
        t("received").replace(
          "{bookmarks}",
          onboarding.bookmarks.toLocaleString(locale()),
        ),
        `received:${onboarding.bookmarks}`,
      );
      appendImportLog(
        enrichment.busy ? t("preparing") : t("retryImport"),
        `${enrichment.busy ? "preparing" : "retry"}:${onboarding.bookmarks}`,
      );
    } else box.textContent = t("waiting");
  }
  function pollImport() {
    clearTimeout(pollTimer);
    checkImport().catch(() => {});
    pollTimer = setTimeout(() => pollImport(), 5000);
  }
  async function reviewCategories() {
    const choices = currentChoices();
    if (!choices.some((item) => item.enabled)) {
      q("#onboarding-error").textContent = t("needOne");
      return;
    }
    localStorage.setItem(
      `xb-taxonomy-${ctx.state.taxonomyDiscovery.run_id}`,
      JSON.stringify(choices),
    );
    await move("category_confirmation");
  }
  function clearActivationTimers() {
    activationTimers.forEach(clearTimeout);
    activationTimers = [];
  }
  function appendActivationLog(message, level = "info") {
    const panel = q("#onboarding-activation-progress"),
      log = q("#onboarding-activation-log");
    if (!panel || !log) return;
    panel.classList.remove("hidden");
    const entry = document.createElement("p");
    entry.className = level;
    entry.innerHTML = `<time>${new Date().toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</time><span>${escape(message)}</span>`;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
  }
  async function activateCategories() {
    const button = q("#onboarding-activate"),
      back = q("#onboarding-back"),
      error = q("#onboarding-error"),
      choices = savedChoices();
    button.disabled = true;
    back.disabled = true;
    button.setAttribute("aria-busy", "true");
    button.textContent = t("activating");
    error.textContent = "";
    appendActivationLog(t("activatePreparing"));
    for (const [delay, key] of [
      [350, "activateCreating"],
      [1400, "activateAssigning"],
      [4500, "activateIndexing"],
      [12000, "activateFinishing"],
    ])
      activationTimers.push(
        setTimeout(() => appendActivationLog(t(key)), delay),
      );
    try {
      await ctx.api("/api/taxonomy/discovery/apply", {
        method: "POST",
        body: JSON.stringify({ categories: choices }),
      });
      clearActivationTimers();
      appendActivationLog(t("activateDone"), "success");
      await patch({ step: "complete" });
      localStorage.removeItem(
        `xb-taxonomy-${ctx.state.taxonomyDiscovery.run_id}`,
      );
      await new Promise((resolve) => setTimeout(resolve, 350));
      root().classList.add("hidden");
      ctx.cache.clear();
      await ctx.bootstrap(false);
      ctx.toast(t("done"));
    } catch (problem) {
      clearActivationTimers();
      appendActivationLog(problem.message, "error");
      error.textContent = problem.message;
      button.disabled = false;
      back.disabled = false;
      button.removeAttribute("aria-busy");
      button.textContent = t("activate");
    }
  }

  async function resume() {
    onboarding = await ctx.api("/api/onboarding");
    if (onboarding.completed) {
      root().classList.add("hidden");
      await ensureApp();
      return;
    }
    window.xbI18n.setLocale(onboarding.locale, {
      persist: true,
      announce: false,
    });
    localStorage.setItem("x-bookmarks-theme", onboarding.theme);
    localStorage.setItem("x-bookmarks-palette", onboarding.palette);
    document.documentElement.dataset.theme = onboarding.theme;
    document.documentElement.dataset.palette = onboarding.palette;
    await ensureApp();
    if (
      onboarding.step === "categories" ||
      onboarding.step === "category_confirmation"
    )
      ctx.state.taxonomyDiscovery = await ctx.api("/api/taxonomy/discovery");
    show(onboarding.step);
    if (onboarding.step === "extension") loadPackage();
    if (onboarding.step === "import") pollImport();
  }
  async function start(context) {
    ctx = context;
    toolbar();
    const response = await fetch("/api/setup/status", {
      credentials: "same-origin",
    });
    const status = await response.json();
    if (status.needs_setup) {
      show("account");
      return;
    }
    try {
      const session = await ctx.api("/api/session");
      ctx.state.csrf = session.csrf;
      await resume();
    } catch {
      root().classList.add("hidden");
      q("#login").classList.remove("hidden");
    }
  }
  q("#onboarding-theme").onclick = async () => {
    const value =
      document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = value;
    localStorage.setItem("x-bookmarks-theme", value);
    window.setTheme?.(value);
    toolbar();
    if (ctx?.state.csrf) await patch({ theme: value });
  };
  q("#onboarding-language").onclick = () =>
    chooseLocale(locale() === "es" ? "en" : "es");
  q("#onboarding-palette").onclick = (event) => {
    event.stopPropagation();
    const menu = q("#onboarding-palette-menu"),
      open = menu.classList.toggle("hidden") === false;
    q("#onboarding-palette").setAttribute("aria-expanded", String(open));
  };
  document.querySelectorAll("[data-onboarding-palette]").forEach(
    (button) =>
      (button.onclick = async () => {
        const value = button.dataset.onboardingPalette;
        document.documentElement.dataset.palette = value;
        localStorage.setItem("x-bookmarks-palette", value);
        window.setPalette?.(value, { persist: true });
        q("#onboarding-palette-menu").classList.add("hidden");
        q("#onboarding-palette").setAttribute("aria-expanded", "false");
        toolbar();
        if (ctx?.state.csrf) await patch({ palette: value });
      }),
  );
  document.addEventListener("pointerdown", (event) => {
    if (!event.target.closest(".onboarding-appearance")) {
      q("#onboarding-palette-menu").classList.add("hidden");
      q("#onboarding-palette").setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("keydown", (event) => {
    if (
      event.key === "Escape" &&
      !q("#onboarding-palette-menu").classList.contains("hidden")
    ) {
      q("#onboarding-palette-menu").classList.add("hidden");
      q("#onboarding-palette").setAttribute("aria-expanded", "false");
      q("#onboarding-palette").focus();
    }
  });
  window.xbOnboarding = { start, resume };
})();
