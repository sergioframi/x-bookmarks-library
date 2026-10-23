(() => {
  const palettes = ["mono", "ice", "lavender", "rose", "coral"];
  try {
    const savedPalette = localStorage.getItem("x-bookmarks-palette");
    const savedTheme = localStorage.getItem("x-bookmarks-theme");
    const savedLanguage = localStorage.getItem("x-bookmarks-language");
    const locale = ["es", "en"].includes(savedLanguage)
      ? savedLanguage
      : (savedTheme || savedPalette
          ? "es"
          : (String(navigator.language || "es").toLowerCase().startsWith("en") ? "en" : "es"));
    document.documentElement.dataset.locale = locale;
    document.documentElement.lang = locale;
    document.documentElement.dataset.palette = palettes.includes(savedPalette) ? savedPalette : "ice";
    document.documentElement.dataset.theme = savedTheme
      || (globalThis.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  } catch {
    document.documentElement.dataset.palette = "ice";
    document.documentElement.dataset.theme = "light";
    document.documentElement.dataset.locale = "es";
    document.documentElement.lang = "es";
  }
})();
