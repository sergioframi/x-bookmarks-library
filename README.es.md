# Biblioteca X

[English version](README.md)

Aplicación privada y autohospedada para importar, clasificar, buscar y organizar
bookmarks de X. Incluye una extensión de Chrome para sincronización directa y
no requiere ningún servicio SaaS.

## Requisitos

- Docker Engine con el complemento Docker Compose.
- Un servidor Linux. El flujo completo está verificado en Raspberry Pi de 64 bits.
- Aproximadamente 1 GB libre en disco y, preferiblemente, 4 GB de RAM.
- Chrome 120 o posterior en el ordenador que mantiene la sesión de X.
- Internet para construir la imagen, descargar el modelo y consultar X.

## Instalación rápida

```sh
git clone https://github.com/sergioframi/x-bookmarks-library.git
cd x-bookmarks-library
docker compose up -d --build
scripts/healthcheck.sh
```

La aplicación estará disponible en `http://<dirección-del-servidor>:8080/`.
Docker Compose construye localmente tanto la aplicación como la extensión. En
el primer arranque se crean automáticamente la base de datos, las migraciones y
un secreto de sesión aleatorio persistente.

El puerto predeterminado es `8080` y no hace falta crear `.env`. Para escoger
otro puerto:

```sh
cp .env.example .env
# Editar PORT en .env y después:
docker compose up -d --build
```

Comandos habituales:

```sh
docker compose logs -f --tail=100 app
docker compose down                 # conserva todos los datos
docker compose up -d --build        # reconstruye después de actualizar
scripts/backup.sh
```

No se debe ejecutar `docker compose down -v` salvo que se quiera eliminar
intencionadamente la base de datos y el modelo descargado.

En la primera visita, el onboarding crea el único usuario y su contraseña. No
se generan ni almacenan credenciales predeterminadas. Después guía la
instalación y el emparejamiento de la extensión, la primera importación, los
embeddings locales y el descubrimiento de categorías.

La contraseña puede cambiarse desde el botón **Contraseña** de la cabecera. Se
solicita la contraseña actual y una nueva de al menos 12 caracteres. El hash se
guarda en SQLite, nunca la contraseña en claro, y el cambio invalida las demás
sesiones abiertas.

El idioma elegido durante el onboarding determina los nombres de las categorías
generadas. Esos nombres forman parte de la biblioteca y no se traducen al cambiar
posteriormente el idioma de la interfaz.

## Datos persistentes

Docker crea tres volúmenes con nombre para la base de datos, el modelo de
embeddings y los logs. El modelo se descarga durante la primera importación y
actualmente ocupa unos 241 MB. Los archivos recibidos desde la extensión se
conservan en el volumen de datos. La carpeta versionada `imports/` se monta en
modo de solo lectura y solo se utiliza para importaciones JSON manuales.

## Instalar y emparejar la extensión

1. Iniciar sesión en la web y pulsar **Sincronización**.
2. Descargar y descomprimir `xarchive-connector.zip`.
3. Abrir `chrome://extensions`, activar el modo desarrollador y elegir
   **Cargar descomprimida**.
4. Mantener abierta la aplicación, generar un código y pulsar el icono de
   xarchive. La extensión toma la dirección privada de la pestaña activa,
   solicita permiso solo para ese host y permite introducir el código.
5. Tras emparejar, usar **Sincronizar ahora** o **Revisión completa** desde la
   propia aplicación. El trabajo se realiza en una pestaña de extensión
   inactiva, sin cambiar la pestaña visible.

La dirección no está codificada en el paquete: puede ser una IP LAN, un nombre
`.local`, DNS interno o una dirección VPN privada. La instalación conserva un
identificador independiente de la URL para detectar cambios o conexiones a un
servidor diferente. En un PC nuevo se repite únicamente el emparejamiento.

La extensión almacena un token revocable por dispositivo. Las cookies,
`auth_token`, `ct0` y cabeceras de X nunca salen de Chrome.

El menú muestra si la extensión está presente en ese Chrome, el dispositivo,
el progreso y el resultado. Tras cada Quick update o Full refresh, el archivo
acumulado y la observación de esa exploración se envían automáticamente. Si la
Raspberry no está disponible, el archivo continúa guardado en IndexedDB.

## Duplicados y eliminaciones

- `tweet_id` es la clave canónica. FTS5 contiene un documento por bookmark y
  los embeddings usan clave única `(tweet_id, modelo)` más hash del contenido.
- Una cita no se convierte en bookmark salvo que también aparezca guardada.
- Repetir el mismo `scan_id` devuelve el recibo previo sin incrementar ausencias
  ni repetir el trabajo.
- Quick updates, snapshots parciales, interrupciones y `pagination_guard` nunca
  dan de baja registros.
- Una primera ausencia en un Full refresh completo marca
  `suspected_removed`; una segunda ausencia completa consecutiva marca
  `removed` y lo excluye de resultados ordinarios.
- Si reaparece se reactiva la misma fila conservando notas, estado, favoritos y
  taxonomía manual.

## Importación manual y mantenimiento

```sh
scripts/import.sh nombre.json
scripts/classify.sh --only-unclassified
scripts/embed.sh
docker compose run --rm app python manage.py rebuild-fts
scripts/backup.sh
```

Los archivos recibidos por sincronización se conservan por hash en
`data/sync-archives/`.

## Arquitectura

- FastAPI, interfaz responsive sin frameworks externos y SQLite WAL/FTS5.
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` con
  FastEmbed/ONNX, vectores normalizados de 384 dimensiones.
- Ranking híbrido RRF con prioridad para coincidencias exactas.
- El encoder de consultas se ejecuta bajo demanda en un subproceso acotado; no
  existe ningún LLM generativo ni modelo residente permanentemente.
- Sesión firmada, PBKDF2, CSRF, CSP, tokens revocables por dispositivo y sin
  telemetría.

## Descubrimiento local de categorías

Una instalación nueva no recibe automáticamente la taxonomía del repositorio. Tras la
primera importación, la aplicación reutiliza los embeddings multilingües y agrupa los
bookmarks con K-Means esférico implementado en NumPy. El proceso se ejecuta una vez,
en local, sin cargar un LLM generativo ni enviar contenido a terceros.

Las categorías se guardan primero como borrador. En el siguiente acceso se muestran
con sus términos y ejemplos representativos para que el usuario pueda desactivarlas,
renombrarlas o editar su descripción antes de confirmar. Solo entonces se crean las
categorías y sus asignaciones. Las importaciones posteriores se clasifican contra los
centroides confirmados; las asignaciones y supresiones manuales siguen teniendo
precedencia y recalibran esos prototipos.

El flujo habitual se ejecuta automáticamente desde `scripts/import.sh` y desde la
sincronización de la extensión. Para crear manualmente el borrador después de haber
generado los embeddings:

```sh
scripts/discover-taxonomy.sh
```

Se requieren al menos 20 bookmarks con embeddings. Una taxonomía activa nunca se
reemplaza automáticamente.

## API de sincronización

- `POST /api/v1/xarchive/pairing-codes` — sesión web + CSRF.
- `GET /api/v1/xarchive/devices` y `DELETE .../{id}` — administrar equipos.
- `POST /api/v1/xarchive/pair` — canjear código de un solo uso.
- `GET /api/v1/xarchive/bootstrap` — restaurar el acumulado en otro PC.
- `POST /api/v1/xarchive/sync` — importación idempotente desde la extensión.
- `GET /api/v1/xarchive/sync/{id}` — recibo y estado del enriquecimiento.

## Límites conocidos

- Los posts no disponibles para la sesión actual de X pueden llegar sin texto
  recuperable.
- La reconciliación de eliminados requiere Full refresh completos; no se infiere
  nada a partir de una actualización rápida o parcial.
- X usa una API privada en la extensión y puede cambiarla. El contenido local se
  conserva aunque falle una actualización futura.
