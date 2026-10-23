# X Bookmarks Library

A private, self-hosted home for your X bookmarks. It imports them through a
Chrome extension, makes them searchable, discovers useful categories locally,
and gives you flexible column-based views.

No SaaS account, telemetry, or generative AI service is required. Your library
stays on your machine.

https://github.com/user-attachments/assets/861fc96a-da7c-478c-8269-584d80d70cb2

## What you get

- Exact full-text search plus multilingual semantic search.
- Filters for categories, tags, authors, content type, dates, media, and links.
- Locally discovered categories based on your own bookmarks.
- Personal states, priorities, favorites, notes, review dates, and tags.
- Custom views with category columns or the complete timeline.
- Light and dark modes, five color palettes, and English or Spanish UI.
- Direct synchronization from Chrome, with progress, logs, and diagnostics.
- SQLite storage, local ONNX embeddings, backups, and no telemetry.

## What you need

- A Linux machine with Docker Engine and Docker Compose.
- Preferably 4 GB of RAM and roughly 1 GB of free disk space.
- Chrome 120 or newer on the computer where you use X.
- Internet access to build the image, download the embedding model, and read
  your bookmarks from X.

The complete flow is tested on a 64-bit Raspberry Pi.

## Install

```sh
git clone https://github.com/sergioframi/x-bookmarks-library.git
cd x-bookmarks-library
docker compose up -d --build
```

Open `http://<your-machine>:8080/`.

Port `8080` is the default. To use a different one:

```sh
cp .env.example .env
```

Edit `PORT` in `.env`, then run the same Compose command:

```sh
docker compose up -d --build
```

The first build is the slow one. Before the web application starts, Compose
downloads, loads, and validates the local embedding model (about 241 MB). The
model is kept in the `library-models` volume, so later starts reuse it instead
of downloading it during onboarding.

On hosts where Docker memory cgroups are enabled, optional container limits can
be set with `MEM_LIMIT` and `MEMSWAP_LIMIT` in `.env`. Leave both at `0` on
Raspberry Pi kernels that do not expose the memory controller.

## First run

The onboarding walks you through everything:

1. Create the installation's only username and password.
2. Pick a language, light or dark mode, and a color palette.
3. Download the included Chrome extension.
4. Load it from `chrome://extensions` using **Load unpacked**, then pair it with
   the library using the temporary code shown on screen.
5. Start the first **Full refresh**. The extension reads bookmarks through your
   existing X session and sends them directly to your private installation.
6. Review the locally discovered categories, rename or disable any you do not
   want, and confirm them.

The language selected during onboarding is also used for generated category
names. Category names are library content, so changing the interface language
later will not translate them.

The first import uses the model prepared during startup. The progress log shows
what the server is doing while it creates embeddings and categories. If that
local processing is interrupted, use **Retry enrichment**: the imported
bookmarks remain available and do not need to be downloaded from X again.

## Using the library

### Timeline and bookmark cards

- Double-click a bookmark card to expand it. The **Expand** button does the same
  thing.
- Use **Organize** to edit its state, priority, favorite status, review date,
  categories, tags, and private notes.
- Quoted posts are shown separately, and the original post remains one click
  away.

### Custom views and columns

- Create a view with one or more category columns, or add **All · general
  timeline**.
- Drag a column by its header handle to reorder it.
- Drag the resize handle on the column's right edge to change its width.
- Double-click that resize handle to restore the default width.
- The column menu lets you edit, move, refresh, or remove a column.
- Views can be renamed, duplicated, selected as the startup view, or deleted.

### Search and filters

Search starts with fast SQLite full-text results and then improves the ranking
with local semantic similarity when available. Exact technical terms still get
priority. If the model cannot run, full-text search keeps working.

Filters can be combined, and selected values within the same filter group work
as alternatives. Active filters remain visible above the results.

### Appearance

Language, light or dark mode, and the color palette can be changed from the
left side of the header at any time.

## Synchronization

Open **Synchronization** in the web app to install or pair the extension, start
a quick or full refresh, inspect progress, and review combined extension/server
logs.

The extension asks for access only to the private address you pair. X cookies,
`auth_token`, `ct0`, and captured request headers stay in Chrome. The server
receives the resulting bookmark archive, not your X credentials.

Use **Sync now** for recent changes and **Full refresh** for a complete pass.
Partial or interrupted scans never imply that a missing bookmark was deleted.
An interrupted full refresh keeps its checkpoint and resumes from the last
confirmed X cursor the next time you start it. Requests are paced from X's
rate-limit headers, so a large archive may take a while without hammering the
API.

## Data and privacy

Docker creates named volumes for the database, model, and logs. Rebuilding the
image or running `docker compose down` keeps them. This command deletes them:

```sh
docker compose down -v
```

Only use it when you genuinely want to erase the installation.

The app is designed for a trusted LAN or private VPN. Do not expose its HTTP
port directly to the public Internet.

## Useful commands

```sh
scripts/healthcheck.sh
docker compose logs -f --tail=100 app
docker compose logs model-init
scripts/backup.sh
docker compose down
docker compose up -d --build
```

To import an existing xarchive JSON manually, place it in `imports/` and run:

```sh
scripts/import.sh archive.json
```

## Update

```sh
git pull
docker compose up -d --build
```

If the extension changed, replace the files in its existing unpacked folder
and click its reload button in `chrome://extensions`. Keeping the same folder
preserves the extension installation and local archive.

## How it works

- FastAPI with a framework-free responsive interface.
- SQLite WAL and FTS5 for storage and exact search.
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` through
  FastEmbed/ONNX for 384-dimensional multilingual embeddings.
- Hybrid reciprocal-rank fusion for exact plus semantic results.
- Spherical K-Means in NumPy for one-time local category discovery.
- Signed sessions, PBKDF2 password hashes, CSRF protection, CSP, and revocable
  device tokens.
- No permanent AI process: the query encoder runs only when needed.

## Current limitations

- The Chrome extension depends on X's private API, which may change.
- Posts unavailable to the current X session may arrive without recoverable
  text.
- Reliable removal detection requires repeated complete Full refresh scans.
- The application is currently designed for one local user.

## Fork and license

The bundled extension is **xarchive · Library Fork**. It is based on the
[original xarchive project](https://github.com/sytelus/xarchive); provenance is
recorded in `extension/xarchive/NOTICE.md` and `release.json`.

The library is distributed under the [MIT License](LICENSE). The bundled
extension keeps its own MIT license, and vendored Dexie keeps its original
Apache 2.0 notice.
