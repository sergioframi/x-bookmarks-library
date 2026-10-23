import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile


STATIC = Path(__file__).parents[1] / "app" / "static"


def compact(value: str) -> str:
    return "".join(value.split())


def test_theme_bootstrap_runs_before_stylesheet_and_assets_are_cache_busted():
    html = (STATIC / "index.html").read_text()
    bootstrap = (STATIC / "bootstrap.js").read_text()
    assert html.index('/static/bootstrap.js') < html.index('rel="stylesheet"')
    assert 'localStorage.getItem("x-bookmarks-theme")' in bootstrap
    assert 'localStorage.getItem("x-bookmarks-language")' in bootstrap
    assert "/static/styles.css?v=20261022-34" in html
    assert "/static/i18n.js?v=20261023-6" in html
    assert "/static/app.js?v=20261022-38" in html


def test_theme_button_is_accessible_and_script_persists_choice():
    html = (STATIC / "index.html").read_text()
    script = (STATIC / "app.js").read_text()
    assert 'id="theme-toggle"' in html
    assert html.index('id="theme-toggle"') < html.index('id="timeline-mode"')
    assert 'aria-label="Activar tema oscuro"' in html
    assert 'aria-pressed="false"' in html
    assert 'localStorage.setItem(themeKey,value)' in compact(script)
    assert 'dark?"☀":"☾"' in compact(script)
    assert 'button.setAttribute("aria-label",label)' in compact(script)


def test_all_palette_previews_are_available_and_persisted():
    html = (STATIC / "index.html").read_text()
    script = (STATIC / "app.js").read_text()
    css = (STATIC / "styles.css").read_text()
    for palette in ("mono", "ice", "lavender", "rose", "coral"):
        assert f'data-palette-choice="{palette}"' in html
        assert f'[data-palette="{palette}"]' in css
    for discarded in ("blue", "violet", "amber", "terracotta"):
        assert f'data-palette-choice="{discarded}"' not in html
    assert "--topbar:#e8eaed" in css
    assert "--topbar:#e3eff8" in css
    assert 'localStorage.setItem(paletteKey,value)' in compact(script)
    assert 'role="menuitemradio"' in html


def test_dark_palette_covers_primary_surfaces():
    css = (STATIC / "styles.css").read_text()
    assert '[data-theme="dark"]' in css
    for selector in (".tweet", "dialog", ".view-column", ".facet>.facet-body", ".login-card"):
        assert selector in css


def test_column_resize_handle_can_restore_default_width():
    html = (STATIC / "index.html").read_text()
    script = (STATIC / "app.js").read_text()
    assert "constdefaultColumnWidth=360" in compact(script)
    assert "handle.ondblclick=(event)=>" in compact(script)
    assert "applyWidth(defaultColumnWidth)" in script
    assert "saveColumnWidth(columnId,defaultColumnWidth)" in compact(script)
    assert "Doble clic para restablecer" in script
    assert "/static/app.js?v=20261022-38" in html


def test_new_view_can_start_with_the_general_timeline():
    script = (STATIC / "app.js").read_text()
    translations = (STATIC / "i18n.js").read_text()
    assert 'type="checkbox" value="__all__"' in script
    assert 'include_all: includeAll' in script
    assert '"Todo · timeline general": "All · general timeline"' in translations


def test_sync_dialog_translates_static_copy_and_server_progress():
    html = (STATIC / "index.html").read_text()
    translations = (STATIC / "i18n.js").read_text()
    static_copy = (
        "La extensión usa la sesión de X de este Chrome y envía los guardados "
        "directamente a esta instalación privada."
    )
    assert f"<p>{static_copy}</p>" in html
    assert f'"{static_copy}": "The extension uses this Chrome browser' in translations
    assert (
        '"Enriquecimiento local completado": "Local enrichment completed"'
        in translations
    )
    address_copy = (
        "La dirección se obtiene de esta pestaña y permanece en Chrome; no se "
        "publica ni se envía a ningún servicio externo."
    )
    assert f"<p>{address_copy}</p>" in html
    assert f'"{address_copy}": "The address is read from this tab' in translations


def test_first_import_taxonomy_review_is_available_and_local():
    html = (STATIC / "index.html").read_text()
    script = (STATIC / "app.js").read_text()
    assert 'id="taxonomy-dialog"' in html
    assert 'id="taxonomy-candidates"' in html
    assert "No se envía contenido a servicios externos" in " ".join(html.split())
    assert 'api("/api/taxonomy/discovery",{method:"POST"})' in compact(script)
    assert 'api("/api/taxonomy/discovery/apply"' in compact(script)


def test_account_and_sync_dialogs_close_on_backdrop_and_revoked_devices_can_be_deleted():
    script = (STATIC / "app.js").read_text()
    assert 'closeOnBackdrop($("#extension-dialog"))' in script
    assert 'closeOnBackdrop($("#password-dialog"))' in script
    assert "data-delete-device" in script
    assert "/record`" in script
    assert "requestDeviceDelete(button.dataset.deleteDevice" in compact(script)
    assert 'kind:"device"' in compact(script)
    assert "El historial y los resultados de sus sincronizaciones se conservarán." in script
    assert "confirm(" not in script


def test_language_toggle_is_accessible_persistent_and_keeps_categories_out_of_catalog():
    html = (STATIC / "index.html").read_text()
    script = (STATIC / "i18n.js").read_text()
    taxonomy = (STATIC.parents[0] / "taxonomy.py").read_text()
    assert 'id="language-toggle"' in html
    assert html.index('id="language-toggle"') < html.index('id="timeline-mode"')
    assert 'aria-label="Cambiar a inglés"' in html
    assert 'data-i18n-skip>EN</button>' in compact(html)
    assert 'x-bookmarks-language' in script
    assert 'localStorage.setItem(STORAGE_KEY, next)' in script
    assert 'document.documentElement.lang = next' in script
    assert 'window.dispatchEvent(new CustomEvent("xb-language-change"' in script
    assert 'setLocale(currentLocale === "es" ? "en" : "es")' in script
    assert 'button.textContent = spanish ? "EN" : "ES"' in script
    assert '"Categorías": "Categories"' in script
    for name in ("Ciberseguridad ofensiva", "IA y agentes", "Desarrollo y sistemas", "Otros intereses"):
        assert name in taxonomy
        assert name not in script


def test_language_change_relocalizes_view_columns_without_reloading_them():
    script = (STATIC / "app.js").read_text()
    handler = script.split('window.addEventListener("xb-language-change"', 1)[1]
    assert "relocalizeVisibleView()" in handler
    assert "renderActiveView()" not in handler
    assert 'data-local-date="${esc(item.created_at||"")}"' in compact(script)
    assert 'data-local-number="${Number(column.count)}"' in compact(script)
    assert 'countNode.dataset.localNumber=String(response.total)' in compact(script)


def test_extension_is_english_only_and_prioritizes_private_library_connection(tmp_path):
    extension = STATIC.parents[1] / "extension" / "xarchive"
    options = (extension / "options.html").read_text()
    viewer = (extension / "viewer.html").read_text()
    manifest = json.loads((extension / "manifest.json").read_text())
    release = json.loads((extension / "release.json").read_text())
    assert 'data-language-select' not in options
    assert 'data-language-select' not in viewer
    assert 'i18n.js' not in options
    assert 'i18n.js' not in viewer
    assert not (extension / "i18n.js").exists()
    assert manifest["name"] == "xarchive · Library Fork"
    assert "default_locale" not in manifest
    assert "Private library" in options
    assert "Raspberry" not in options
    assert options.index('id="connector-section"') < options.index('id="controls-section"')
    assert options.index('id="connector-section"') < options.index('id="library-section"')
    assert '<details id="library-section"' in options
    assert '<details id="log-section"' in options
    assert manifest["version"] == "1.1.0.1"
    assert manifest["version_name"] == "1.1.0-fork.1"
    assert release["upstream_version"] == "1.1.0"
    assert release["fork_revision"] == 1
    assert "export const VERSION = '1.1.0-fork.1'" in (extension / "version.js").read_text()
    assert "Original project: sytelus/xarchive" in options
    assert (extension / "NOTICE.md").is_file()
    package_path=tmp_path/"xarchive-connector.zip"
    subprocess.run(
        [sys.executable,str(STATIC.parents[1]/"scripts"/"build-extension-package.py"),
         "--source",str(extension),"--destination",str(package_path)],
        check=True,
    )
    with ZipFile(package_path) as package:
        names = set(package.namelist())
        assert "i18n.js" not in names
        assert {"NOTICE.md", "release.json"}.issubset(names)
        assert not any(name.startswith("_locales/") for name in names)
        assert not any(name.startswith("docs/") or name.startswith(".github/") for name in names)


def test_first_run_onboarding_exposes_account_preferences_and_confirmation():
    html = (STATIC / "index.html").read_text()
    script = (STATIC / "onboarding.js").read_text()
    assert 'id="onboarding"' in html
    assert 'id="onboarding-theme"' in html
    assert 'id="onboarding-palette"' in html
    assert 'id="onboarding-language"' in html
    assert html.index('id="onboarding-theme"') < html.index('id="onboarding-content"')
    assert html.index('id="onboarding-palette"') < html.index('id="onboarding-content"')
    assert 'data-onboarding-palette="coral"' in html
    assert 'localStorage.setItem("x-bookmarks-palette",value)' in compact(script)
    assert 'class="onboarding-import-log"' in script
    assert 'role="log"' in script
    assert 'job.pages' in script
    assert 'id="onboarding-check-import"' not in script
    assert 'category_confirmation' in script
    assert 'let currentStep = "account"' in script
    assert 'render(currentStep)' in script
    assert 'no se traducirán automáticamente' in script
    assert 'will not be translated automatically' in script
    assert 'onboarding.enrichment||{}' in compact(script)
    assert 'id="onboarding-extension-progress"' in script
    assert 'id="onboarding-extension-diagnostics"' in script
    assert 'connector.logs||[]' in compact(script)
    assert 'importLaunchPending||extensionRunning||Boolean(enrichment.busy)' in compact(script)
    assert 'id="onboarding-activation-progress"' in script
    assert 'id="onboarding-activation-log"' in script
    assert 'activateAssigning' in script
    assert '.primary:disabled' in (STATIC / "styles.css").read_text()


def test_sync_dialog_exposes_server_progress_diagnostics_and_combined_log():
    html = (STATIC / "index.html").read_text()
    script = (STATIC / "app.js").read_text()
    for element_id in ("server-enrichment", "server-progress-bar", "sync-diagnostics", "sync-combined-log"):
        assert f'id="{element_id}"' in html
    assert 'api("/api/enrichment")' in compact(script)
    assert "serverEnrichment?.busy" in script
    assert 'role="log"' in html


def test_extension_bridges_complete_progress_without_overwriting_logs():
    extension = STATIC.parents[1] / "extension" / "xarchive"
    options = (extension / "options.js").read_text()
    connector = (extension / "lib" / "library-sync.js").read_text()
    for field in ("folders: statFolders.textContent", "speed: statSpeed.textContent", "elapsedSeconds"):
        assert field in options
    assert "let connectorWrite = Promise.resolve()" in connector
    assert "function updateConnector(change)" in connector
    assert "config.logs =" in connector
