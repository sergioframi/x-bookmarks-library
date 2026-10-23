(() => {
  "use strict";

  const STORAGE_KEY = "x-bookmarks-language";
  const SUPPORTED = new Set(["es", "en"]);
  const ATTRIBUTES = ["aria-label", "placeholder", "title", "data-tooltip"];

  // Categories are intentionally absent: their stored names must remain unchanged.
  const EN = {
    "Biblioteca X": "X Library",
    "Idioma": "Language",
    "Cambiar a inglés": "Switch to English",
    "Cambiar a español": "Switch to Spanish",
    "Saltar a resultados": "Skip to results",
    "Tu biblioteca privada": "Your private library",
    "Todo lo que guardaste en X, organizado y fácil de encontrar.": "Everything you saved on X, organized and easy to find.",
    "Usuario": "Username",
    "Contraseña": "Password",
    "Entrar": "Sign in",
    "Abrir filtros": "Open filters",
    "Activar tema oscuro": "Switch to dark theme",
    "Activar tema claro": "Switch to light theme",
    "Tema oscuro": "Dark theme",
    "Tema claro": "Light theme",
    "Previsualizar paletas": "Preview palettes",
    "Paletas": "Palettes",
    "Paletas de color": "Color palettes",
    "Previsualizar paleta": "Preview palette",
    "Combínala con claro u oscuro": "Use it with light or dark mode",
    "Monocroma": "Monochrome",
    "Grises limpios y neutros": "Clean, neutral grays",
    "Azul hielo": "Ice blue",
    "Fría, ligera y minimalista": "Cool, light and minimal",
    "Lavanda nube": "Cloud lavender",
    "Suave y contemporánea": "Soft and contemporary",
    "Rosa cuarzo": "Rose quartz",
    "Serena y ligeramente cálida": "Calm and subtly warm",
    "Arena y coral": "Sand and coral",
    "Luminosa y editorial": "Bright and editorial",
    "Vista principal": "Main view",
    "Vistas": "Views",
    "Abrir sincronización": "Open synchronization",
    "Sincronización": "Synchronization",
    "Cambiar contraseña": "Change password",
    "Salir": "Sign out",
    "Busca una tecnología, problema o idea…": "Search for a technology, problem or idea…",
    "Buscar en la biblioteca": "Search the library",
    "Enfocar la búsqueda": "Focus search",
    "Filtros": "Filters",
    "Filtros activos": "Active filters",
    "Filtros de búsqueda": "Search filters",
    "Explorar": "Explore",
    "Combina opciones para acotar tu biblioteca. Dentro de cada grupo se acepta cualquiera de las seleccionadas.": "Combine options to narrow down your library. Within each group, any selected option may match.",
    "Sin filtros activos": "No active filters",
    "Restablecer": "Reset",
    "Categorías": "Categories",
    "Revisar categorías": "Review categories",
    "Organización local": "Local organization",
    "Descubrir tus categorías": "Discover your categories",
    "Analizamos los embeddings de esta biblioteca en la Raspberry. No se envía contenido a servicios externos.": "This library's embeddings are analyzed locally. No content is sent to external services.",
    "Descubrir categorías": "Discover categories",
    "Nombre": "Name",
    "Descripción": "Description",
    "Ver ejemplos": "View examples",
    "Usar estas categorías": "Use these categories",
    "Áreas temáticas amplias": "Broad subject areas",
    "Buscar categoría": "Search categories",
    "Buscar categoría…": "Search categories…",
    "Buscar una categoría…": "Search a category…",
    "Buscar una categoría": "Search a category",
    "Etiquetas": "Tags",
    "Tecnologías y conceptos concretos": "Specific technologies and concepts",
    "Buscar etiqueta": "Search tags",
    "Autores": "Authors",
    "Cuenta que publicó el contenido": "Account that posted the content",
    "Buscar autor": "Search authors",
    "Formato": "Format",
    "Qué tipo de recurso es": "Type of resource",
    "Contenido y fecha": "Content and date",
    "Propiedades adicionales": "Additional properties",
    "Con multimedia": "With media",
    "Con enlaces": "With links",
    "Desde": "From",
    "Hasta": "To",
    "Ver resultados": "View results",
    "Tu archivo personal": "Your personal archive",
    "Guardados": "Bookmarks",
    "Anterior": "Previous",
    "Siguiente": "Next",
    "← Anterior": "← Previous",
    "Siguiente →": "Next →",
    "Cerrar filtros": "Close filters",
    "Vistas personalizadas": "Custom views",
    "Seleccionar o crear una vista": "Select or create a view",
    "Acciones de la vista": "View actions",
    "Añadir columna": "Add column",
    "Refrescar todas las columnas": "Refresh all columns",
    "Renombrar vista": "Rename view",
    "Duplicar vista": "Duplicate view",
    "Usar como vista de inicio": "Use as startup view",
    "Eliminar vista": "Delete view",
    "Tu propio TweetDeck": "Your own TweetDeck",
    "Crea una vista por categorías": "Create a category view",
    "Añade varias columnas, ordénalas arrastrando y guarda el panel para todos tus dispositivos.": "Add several columns, reorder them by dragging, and save the board for all your devices.",
    "Crear primera vista": "Create first view",
    "Cerrar": "Close",
    "Organización": "Organization",
    "Organizar publicación": "Organize post",
    "Guardado": "Saved",
    "Este navegador y esta biblioteca": "This browser and this library",
    "Sincronización con X": "Synchronization with X",
    "La extensión usa la sesión de X de este Chrome y envía los guardados directamente a esta instalación privada.": "The extension uses this Chrome browser's X session and sends bookmarks directly to this private installation.",
    "Comprobando extensión…": "Checking extension…",
    "Esperando respuesta de Chrome.": "Waiting for Chrome.",
    "Sincronizar ahora": "Sync now",
    "Revisión completa": "Full refresh",
    "Preparando…": "Preparing…",
    "Procesamiento local": "Local processing",
    "Procesamiento local en curso": "Local processing in progress",
    "La Raspberry está procesando la biblioteca.": "The local server is processing the library.",
    "Procesando localmente…": "Processing locally…",
    "Diagnóstico": "Diagnostics",
    "Log": "Log",
    "Servidor": "Server",
    "Cuenta de X": "X account",
    "Credenciales": "Credentials",
    "Consulta Bookmarks": "Bookmarks query",
    "Embeddings": "Embeddings",
    "Taxonomía": "Taxonomy",
    "Último latido": "Last heartbeat",
    "Ocupado": "Busy",
    "Disponible": "Available",
    "Detectada": "Detected",
    "No detectada": "Not detected",
    "Disponibles": "Available",
    "No disponibles": "Unavailable",
    "Pendiente": "Pending",
    "extensión": "extension",
    "servidor": "server",
    "Sincronización recibida; preparando embeddings": "Synchronization received; preparing embeddings",
    "Iniciando el modelo local de embeddings": "Starting the local embedding model",
    "Modelo local de embeddings iniciado": "Local embedding model started",
    "Descubriendo categorías localmente": "Discovering categories locally",
    "Descubrimiento local de temas iniciado": "Local topic discovery started",
    "Cargando vectores para descubrir temas": "Loading vectors to discover topics",
    "Seleccionando agrupaciones temáticas": "Selecting topic clusters",
    "Clasificando nuevos bookmarks": "Classifying new bookmarks",
    "Enriquecimiento local completado": "Local enrichment completed",
    "El enriquecimiento no pudo completarse": "Local enrichment could not be completed",
    "El proceso se interrumpió al detener la aplicación": "The process was interrupted when the application stopped",
    "Todavía no hay eventos registrados.": "No events have been recorded yet.",
    "Ya hay una sincronización o enriquecimiento en curso": "A synchronization or enrichment job is already running",
    "La sincronización ya estaba en curso": "Synchronization was already running",
    "Instalar o conectar la extensión": "Install or connect the extension",
    "La dirección se obtiene de esta pestaña y permanece en Chrome; no se publica ni se envía a ningún servicio externo.": "The address is read from this tab and stays in Chrome; it is not published or sent to any external service.",
    "Cargando paquete…": "Loading package…",
    "Descarga, descomprime e instala el ZIP desde": "Download, extract, and install the ZIP from",
    "usando": "using",
    "Cargar descomprimida": "Load unpacked",
    "Mantén esta aplicación abierta y genera el código temporal.": "Keep this application open and generate the temporary code.",
    "Pulsa una vez el icono de xarchive: la extensión reconocerá esta dirección privada.": "Click the xarchive icon once: the extension will recognize this private address.",
    "Pega el código y confirma": "Paste the code and confirm",
    "Emparejar": "Pair",
    "Las siguientes sincronizaciones se iniciarán desde aquí.": "Future synchronizations will start here.",
    ". Las siguientes sincronizaciones se iniciarán desde aquí.": ". Future synchronizations will start here.",
    "Generar código de emparejamiento": "Generate pairing code",
    "Última actividad": "Latest activity",
    "Todavía no hay sincronizaciones registradas.": "No synchronizations have been recorded yet.",
    "Dispositivos": "Devices",
    "Dispositivo": "Device",
    "Seguridad de la cuenta": "Account security",
    "Cambiar contraseña": "Change password",
    "Al guardar se cerrarán las demás sesiones abiertas. Este navegador seguirá conectado.": "Saving will sign out all other open sessions. This browser will remain signed in.",
    "Contraseña actual": "Current password",
    "Nueva contraseña": "New password",
    "Mínimo 12 caracteres.": "At least 12 characters.",
    "Repetir nueva contraseña": "Repeat new password",
    "Guardar nueva contraseña": "Save new password",
    "Nueva vista": "New view",
    "Nombre de la vista": "View name",
    "Ej. Tecnología y aprendizaje": "E.g. Technology and learning",
    "Columnas iniciales": "Initial columns",
    "Selecciona una o varias categorías": "Select one or more categories",
    "Crear vista": "Create view",
    "Contenido de la columna": "Column content",
    "Contenido": "Content",
    "Elige la timeline general o una categoría concreta.": "Choose the general timeline or a specific category.",
    "Título personalizado": "Custom title",
    "Opcional": "Optional",
    "Usar el nombre del contenido": "Use the content name",
    "Confirmar eliminación": "Confirm deletion",
    "¿Eliminar este elemento?": "Delete this item?",
    "Cancelar": "Cancel",
    "Eliminar": "Delete",
    "Herramienta": "Tool",
    "Artículo": "Article",
    "Hilo": "Thread",
    "Tutorial": "Tutorial",
    "Referencia": "Reference",
    "Vídeo": "Video",
    "Imagen": "Image",
    "Otro": "Other",
    "Sesión caducada": "Session expired",
    "No se pudo cargar la biblioteca": "Could not load the library",
    "La nueva contraseña debe tener al menos 12 caracteres.": "The new password must be at least 12 characters long.",
    "Las contraseñas nuevas no coinciden.": "The new passwords do not match.",
    "Contraseña actualizada": "Password updated",
    "La extensión no respondió": "The extension did not respond",
    "Extensión no detectada": "Extension not detected",
    "Extensión instalada, sin conectar": "Extension installed, not connected",
    "Empareja este navegador con la dirección privada actual.": "Pair this browser with the current private address.",
    "Extensión conectada": "Extension connected",
    "Conectada a otra instalación": "Connected to another installation",
    "Vuelve a emparejar la extensión con esta biblioteca privada.": "Pair the extension with this private library again.",
    "Dispositivo revocado": "Device revoked",
    "Dispositivo eliminado": "Device removed",
    "Genera un código nuevo para volver a conectar este Chrome.": "Generate a new code to reconnect this Chrome browser.",
    "Sincronización en curso": "Synchronization in progress",
    "Revisando toda la colección y las carpetas.": "Checking the entire collection and all folders.",
    "Buscando guardados recientes.": "Checking recent bookmarks.",
    "La última sincronización falló": "The last synchronization failed",
    "Abre xarchive para revisar la sesión de X.": "Open xarchive to check the X session.",
    "Sincronización completada": "Synchronization completed",
    "ahora": "now",
    "Sincronizando…": "Synchronizing…",
    "Revisión completa iniciada": "Full refresh started",
    "Sincronización iniciada": "Synchronization started",
    "Reintentar procesamiento local": "Retry local processing",
    "Procesamiento local reanudado": "Local processing resumed",
    "Versión": "Version",
    "Descargar extensión": "Download extension",
    "Revocado": "Revoked",
    "nunca": "never",
    "desconocida": "unknown",
    "Revocar": "Revoke",
    "Todavía no hay dispositivos emparejados.": "No devices have been paired yet.",
    "Mostrar menos": "Show less",
    "Buscando coincidencias exactas…": "Searching exact matches…",
    "Resultados FTS5 listos · calculando similitud semántica…": "FTS5 results ready · calculating semantic similarity…",
    "Orden de guardado de X · FTS5 listo": "X bookmark order · FTS5 ready",
    "Ranking híbrido listo": "Hybrid ranking ready",
    "· consulta en caché": "· cached query",
    "· código copiado": "· code copied",
    "Semántica no disponible · FTS5 sigue activo": "Semantic search unavailable · FTS5 remains active",
    "Coincidencia solo en la cita": "Match only in quoted post",
    "Cita": "Quote",
    "contexto": "context",
    "Contexto no disponible en la exportación": "Context unavailable in the export",
    "Filtrar por formato": "Filter by format",
    "Filtrar por autor": "Filter by author",
    "Doble clic para expandir": "Double-click to expand",
    "Autor no disponible": "Author unavailable",
    "Publicación no disponible en la exportación": "Post unavailable in the export",
    "Expandir": "Expand",
    "Organizar": "Organize",
    "Abrir en X": "Open on X",
    "Abrir en X ↗": "Open on X ↗",
    "Abrir enlace ↗": "Open link ↗",
    "Abrir cita ↗": "Open quote ↗",
    "Semántica": "Semantic",
    "Orden de X": "X order",
    "cita": "quote",
    "No hay resultados con estos criterios.": "No results match these criteria.",
    "Publicación completa": "Full post",
    "Publicación": "Post",
    "Publicación no disponible": "Post unavailable",
    "Enlace destacado": "Featured link",
    "Tarjeta": "Card",
    "Abrir enlace": "Open link",
    "Publicación citada": "Quoted post",
    "Contexto no disponible": "Context unavailable",
    "Abrir cita": "Open quote",
    "Pendiente…": "Pending…",
    "Guardando…": "Saving…",
    "No se pudo guardar": "Could not save",
    "General": "General",
    "General ·": "General ·",
    "Ninguna categoría seleccionada": "No categories selected",
    "Sin etiquetas": "No tags",
    "Clasificación múltiple": "Multiple classification",
    "disponibles": "available",
    "Conceptos concretos": "Specific concepts",
    "Buscar o crear etiqueta…": "Search or create a tag…",
    "Añadir": "Add",
    "Notas privadas": "Private notes",
    "Añade contexto para ti…": "Add context for yourself…",
    "Sin vistas guardadas": "No saved views",
    "＋ Nueva vista": "＋ New view",
    "Vista de inicio": "Startup view",
    "Esta es la vista de inicio": "This is the startup view",
    "Arrastrar columna": "Drag column",
    "Opciones de columna": "Column options",
    "Editar columna": "Edit column",
    "Mover a la izquierda": "Move left",
    "Mover a la derecha": "Move right",
    "Eliminar columna": "Delete column",
    "Cargando publicaciones…": "Loading posts…",
    "Cargar más": "Load more",
    "Arrastra para cambiar el ancho · doble clic para restablecer": "Drag to resize · double-click to reset",
    "Añadir una columna": "Add a column",
    "Elige una categoría para este espacio": "Choose a category for this space",
    "No hay publicaciones en esta columna.": "There are no posts in this column.",
    "Reintentar": "Retry",
    "Columna actualizada": "Column updated",
    "No se pudo actualizar la columna": "Could not update the column",
    "Esperando actualización…": "Waiting to update…",
    "Todas las columnas están actualizadas": "All columns are up to date",
    "Ancho de columna restablecido": "Column width reset",
    "Guardar nombre": "Save name",
    "Crear copia": "Create copy",
    "Vista": "View",
    "copia": "copy",
    "Escribe un nombre para la vista.": "Enter a name for the view.",
    "Selecciona al menos una columna para crear la vista.": "Select at least one column to create the view.",
    "Vista renombrada": "View renamed",
    "Vista guardada": "View saved",
    "Todo · timeline general": "All · general timeline",
    "Todas las fuentes ya tienen una columna": "All sources already have a column",
    "Guardar columna": "Save column",
    "La columna desaparecerá de esta vista personalizada.": "The column will be removed from this custom view.",
    "La categoría, los tuits y tus cambios de organización se conservarán.": "The category, posts, and your organization changes will be preserved.",
    "La disposición de columnas de esta vista se eliminará de todos tus dispositivos.": "This view's column layout will be removed from all your devices.",
    "Los tuits, categorías, etiquetas y otras vistas se conservarán.": "Posts, categories, tags, and other views will be preserved.",
    "El dispositivo revocado desaparecerá de esta lista y su credencial dejará de almacenarse.": "The revoked device will disappear from this list and its credential will no longer be stored.",
    "El historial y los resultados de sus sincronizaciones se conservarán.": "Its synchronization history and results will be preserved.",
    "Eliminar dispositivo": "Delete device",
    "Columna eliminada": "Column deleted",
    "Vista eliminada": "View deleted",
    "Esta ya es tu vista de inicio": "This is already your startup view",
    "Vista de inicio actualizada": "Startup view updated",
    "La contraseña actual no es correcta": "The current password is incorrect",
    "La nueva contraseña debe tener al menos 12 caracteres": "The new password must be at least 12 characters long",
    "La nueva contraseña debe ser diferente de la actual": "The new password must be different from the current password",
    "La contraseña cambió durante la operación; inténtalo de nuevo": "The password changed during the operation; please try again",
    "Autenticación requerida": "Authentication required",
    "La sesión ya no es válida": "The session is no longer valid",
    "CSRF inválido": "Invalid CSRF token",
    "Dispositivo no autorizado": "Unauthorized device",
    "Vista no encontrada": "View not found",
    "La categoría seleccionada no existe": "The selected category does not exist",
    "El nombre de la vista no puede estar vacío": "The view name cannot be empty",
    "Columna no encontrada": "Column not found",
    "Dispositivo no encontrado o ya revocado": "Device not found or already revoked",
    "Dispositivo no encontrado": "Device not found",
    "Revoca el dispositivo antes de eliminarlo": "Revoke the device before deleting it",
    "Todavía no hay un archivo para inicializar la extensión": "There is no archive available to initialize the extension yet",
    "Sincronización no encontrada": "Synchronization not found",
    "Paquete de extensión no disponible": "Extension package unavailable"
    ,"La extensión no está emparejada.": "The extension is not paired."
    ,"La orden procede de una instalación distinta.": "The request comes from a different installation."
    ,"Preparando la sincronización": "Preparing synchronization"
    ,"La extensión no está emparejada con esta instalación.": "The extension is not paired with this installation."
    ,"No se pudo iniciar la sincronización.": "Could not start synchronization."
    ,"Empareje primero la extensión con la biblioteca.": "Pair the extension with the library first."
    ,"Chrome no concedió acceso al servidor de la biblioteca.": "Chrome did not grant access to the library server."
    ,"No se pudo activar la conexión con la página.": "Could not activate the connection to the page."
    ,"Este dispositivo fue revocado o su token ya no es válido.": "This device was revoked or its token is no longer valid."
    ,"Preparando la conexión con X": "Preparing the X connection"
    ,"Leyendo guardados de X": "Reading X bookmarks"
    ,"Credenciales incorrectas": "Incorrect credentials"
    ,"filtro numérico inválido": "Invalid numeric filter"
    ,"Bookmark no encontrado": "Bookmark not found"
    ,"categoría desconocida": "Unknown category"
    ,"El nombre de la vista es demasiado largo": "The view name is too long"
    ,"Esta fuente ya tiene una columna en la vista": "This source already has a column in the view"
    ,"El orden debe incluir exactamente las columnas de la vista": "The order must include exactly the columns in the view"
    ,"Paquete no encontrado": "Package not found"
    ,"código de emparejamiento inválido o caducado": "Invalid or expired pairing code"
    ,"archivo xarchive inválido": "Invalid xarchive archive"
    ,"solo se admite xarchive schema 2": "Only xarchive schema 2 is supported"
    ,"el archivo pertenece a otra cuenta de X": "The archive belongs to another X account"
    ,"todos los tweet_id deben ser strings": "All tweet_id values must be strings"
    ,"el archivo acumulado supera el límite de 30 MiB": "The accumulated archive exceeds the 30 MiB limit"
    ,"scan_id inválido": "Invalid scan_id"
    ,"encoder ocupado; se usa FTS5": "Encoder busy; using FTS5"
    ,"encoder ocupado por otro proceso; se usa FTS5": "Encoder busy in another process; using FTS5"
    ,"consulta semántica vacía": "Empty semantic query"
    ,"respuesta inválida del encoder; se usa FTS5": "Invalid encoder response; using FTS5"
    ,"modelo inesperado; se usa FTS5": "Unexpected model; using FTS5"
  };

  const englishPatterns = [
    [/^Previsualizar paletas\. Actual: (.+)$/u, "Preview palettes. Current: $1"],
    [/^Paleta: (.+)$/u, "Palette: $1"],
    [/^No se pudo cargar la biblioteca: (.+)$/u, "Could not load the library: $1"],
    [/^Instálala o conéctala a (.+)\.$/u, "Install it or connect it to $1."],
    [/^Versión (.+)\.$/u, "Version $1."],
    [/^(\d+) nuevos · (\d+) actualizados · (.+)\.$/u, "$1 new · $2 updated · $3."],
    [/^Sincronización: (.+)$/u, "Synchronization: $1"],
    [/^Importación recibida: (\d+) documentos preparados$/u, "$1 documents received and prepared"],
    [/^Nombrando categoría (\d+) de (\d+)$/u, "Naming category $1 of $2"],
    [/^Borrador preparado con (\d+) categorías$/u, "Draft prepared with $1 categories"],
    [/^Error de enriquecimiento: (.+)$/u, "Enrichment error: $1"],
    [/^actualizado (.+)$/u, "updated $1"],
    [/^(\d+) guardados$/u, "$1 bookmarks"],
    [/^(\d+) páginas$/u, "$1 pages"],
    [/^(.+) · (\d+) nuevos · (\d+) actualizados · (\d+) eliminados confirmados$/u, "$1 · $2 new · $3 updated · $4 confirmed removed"],
    [/^(.+) · caduca (.+?)( · código copiado)?$/u, (_, origin, time, copied) => `${origin} · expires at ${time}${copied ? " · code copied" : ""}`],
    [/^Último contacto: (.+)$/u, "Last seen: $1"],
    [/^Ver las (\d+) etiquetas$/u, "View all $1 tags"],
    [/^Ver los (\d+) autores$/u, "View all $1 authors"],
    [/^(\d+) resultados$/u, "$1 results"],
    [/^Ver (\d+) resultados$/u, "View $1 results"],
    [/^Página (\d+)$/u, "Page $1"],
    [/^Cita · (.+)$/u, "Quote · $1"],
    [/^Coincidencia solo en la cita · (.+)$/u, "Match only in quoted post · $1"],
    [/^Publicación citada · (.+)$/u, "Quoted post · $1"],
    [/^Filtrar por (.+)$/u, "Filter by $1"],
    [/^Columna (.+)$/u, "Column $1"],
    [/^Arrastrar (.+)$/u, "Drag $1"],
    [/^Refrescar (.+)$/u, "Refresh $1"],
    [/^Cambiar ancho de (.+)\. Doble clic para restablecer$/u, "Resize $1. Double-click to reset"],
    [/^(\d+) columnas no se pudieron actualizar$/u, "$1 columns could not be updated"],
    [/^1 columna no se pudo actualizar$/u, "1 column could not be updated"],
    [/^¿Eliminar la columna “(.+)”\?$/u, "Delete the “$1” column?"],
    [/^¿Eliminar la vista “(.+)”\?$/u, "Delete the “$1” view?"],
    [/^¿Eliminar el dispositivo “(.+)”\?$/u, "Delete the “$1” device?"],
    [/^Desde (.+)$/u, "From $1"],
    [/^Hasta (.+)$/u, "To $1"],
    [/^(\d+) filtro activo$/u, "$1 active filter"],
    [/^(\d+) filtros activos$/u, "$1 active filters"],
    [/^Enfocar la búsqueda con (.+)$/u, "Focus search with $1"],
    [/^Error: (.+)$/u, "Error: $1"],
    [/^No se pudo descargar el archivo inicial \(HTTP (\d+)\)\.$/u, "Could not download the initial archive (HTTP $1)."],
    [/^Sincronización rechazada \(HTTP (\d+)\)\.$/u, "Synchronization rejected (HTTP $1)."],
    [/^el encoder superó (.+); se usa FTS5$/u, "The encoder exceeded $1; using FTS5"],
    [/^no se pudo iniciar el encoder: (.+)$/u, "Could not start the encoder: $1"],
    [/^falló el encoder \((.+)\); se usa FTS5$/u, "The encoder failed ($1); using FTS5"],
    [/^error semántico \((.+)\); se usa FTS5$/u, "Semantic error ($1); using FTS5"]
  ];

  const ES = {
    completed: "completada",
    running: "en curso",
    error: "error",
    failed: "fallida"
  };

  const textOriginals = new WeakMap();
  const attributeOriginals = new WeakMap();
  let currentLocale;
  let observer;

  function isLibraryContent(node) {
    const element = node?.nodeType === Node.ELEMENT_NODE ? node : node?.parentElement;
    return Boolean(element?.closest(".tweet-text,.author,.handle,.reader-card strong,.reader-card p,.reader-head h2,.reader-urls,.chip.category,.chip:not(.type),[data-i18n-skip]"));
  }

  function initialLocale() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (SUPPORTED.has(saved)) return saved;
      if (localStorage.getItem("x-bookmarks-theme") || localStorage.getItem("x-bookmarks-palette")) return "es";
    } catch {}
    return String(navigator.language || "es").toLowerCase().startsWith("en") ? "en" : "es";
  }

  function translate(source, locale = currentLocale) {
    if (typeof source !== "string") return source;
    if (locale === "es") return ES[source] || source;
    const direct = EN[source];
    if (direct) return direct;
    for (const [pattern, replacement] of englishPatterns) {
      if (pattern.test(source)) return source.replace(pattern, replacement);
    }
    return source;
  }

  function translateTextNode(node, force = false) {
    if (!node?.data || !node.data.trim() || isLibraryContent(node)) return;
    const previous = textOriginals.get(node);
    const rendered = previous ? translate(previous, currentLocale) : null;
    if (!force && previous && node.data === rendered) return;
    if (!previous || (!force && node.data !== rendered)) textOriginals.set(node, node.data);
    const original = textOriginals.get(node);
    const leading = original.match(/^\s*/u)?.[0] || "";
    const trailing = original.match(/\s*$/u)?.[0] || "";
    const core = original.slice(leading.length, original.length - trailing.length || undefined);
    const next = `${leading}${translate(core)}${trailing}`;
    if (node.data !== next) node.data = next;
  }

  function translateAttribute(element, attribute, force = false) {
    if (!element.hasAttribute?.(attribute) || isLibraryContent(element)) return;
    let originals = attributeOriginals.get(element);
    if (!originals) {
      originals = new Map();
      attributeOriginals.set(element, originals);
    }
    const current = element.getAttribute(attribute);
    const previous = originals.get(attribute);
    const rendered = previous == null ? null : translate(previous);
    if (!force && previous != null && current === rendered) return;
    if (previous == null || (!force && current !== rendered)) originals.set(attribute, current);
    const next = translate(originals.get(attribute));
    if (current !== next) element.setAttribute(attribute, next);
  }

  function translateTree(root, force = false) {
    if (!root) return;
    if (root.nodeType === Node.TEXT_NODE) {
      translateTextNode(root, force);
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) return;
    if (root.nodeType === Node.ELEMENT_NODE) {
      for (const attribute of ATTRIBUTES) translateAttribute(root, attribute, force);
    }
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (node.nodeType === Node.TEXT_NODE) translateTextNode(node, force);
      else for (const attribute of ATTRIBUTES) translateAttribute(node, attribute, force);
    }
  }

  function setLocale(locale, { persist = true, announce = true } = {}) {
    const next = SUPPORTED.has(locale) ? locale : "es";
    currentLocale = next;
    document.documentElement.lang = next;
    document.documentElement.dataset.locale = next;
    if (persist) {
      try { localStorage.setItem(STORAGE_KEY, next); } catch {}
    }
    observer?.disconnect();
    translateTree(document, true);
    observer?.observe(document.documentElement, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ATTRIBUTES
    });
    updateLanguageButton();
    if (announce) window.dispatchEvent(new CustomEvent("xb-language-change", { detail: { locale: next } }));
  }

  function updateLanguageButton() {
    const button = document.getElementById("language-toggle");
    if (!button) return;
    const spanish = currentLocale === "es";
    button.textContent = spanish ? "EN" : "ES";
    button.setAttribute("aria-label", spanish ? "Cambiar a inglés" : "Switch to Spanish");
    button.dataset.tooltip = spanish ? "English" : "Español";
  }

  function number(value) {
    return new Intl.NumberFormat(currentLocale === "en" ? "en" : "es").format(value);
  }

  function init() {
    observer = new MutationObserver(records => {
      observer.disconnect();
      for (const record of records) {
        if (record.type === "characterData") translateTextNode(record.target);
        else if (record.type === "attributes") translateAttribute(record.target, record.attributeName);
        else for (const node of record.addedNodes) translateTree(node);
      }
      observer.observe(document.documentElement, {
        subtree: true,
        childList: true,
        characterData: true,
        attributes: true,
        attributeFilter: ATTRIBUTES
      });
    });
    setLocale(currentLocale, { persist: false, announce: false });
    document.getElementById("language-toggle")?.addEventListener("click", () => {
      setLocale(currentLocale === "es" ? "en" : "es");
    });
  }

  currentLocale = initialLocale();
  document.documentElement.lang = currentLocale;
  document.documentElement.dataset.locale = currentLocale;
  window.xbI18n = { locale: () => currentLocale, setLocale, translate, number, translateTree };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
