# Deployment

## Local build

The supported installation path builds the image directly from the checked-out
source:

```sh
docker compose up -d --build
```

The host port defaults to `8080`. To select a different port, copy
`.env.example` to `.env`, change `PORT`, and run the same command. The internal
container port always remains `8080`.

Compose creates named volumes for application data, model files, and logs. The
application generates its session secret on first startup and stores it in the
data volume. Rebuilding the image or running `docker compose down` preserves
all of them. Running `docker compose down -v` permanently removes them.

## Operations

```sh
docker compose ps
docker compose logs -f --tail=100 app
scripts/healthcheck.sh
scripts/backup.sh
docker compose down
```

Place optional manual xarchive JSON files in `imports/` and invoke
`scripts/import.sh <filename>`. Direct extension synchronization does not need
this directory.

## Network boundary

The application is designed for a trusted LAN or private VPN. It serves HTTP by
default and must not be port-forwarded directly to the public Internet. A
deployment behind a private HTTPS reverse proxy should set `COOKIE_SECURE=true`
in `.env`.

## First import

The first full synchronization downloads the multilingual ONNX embedding model
into the model volume, creates the text and vector indexes, and prepares a local
category draft. The current model cache uses approximately 241 MB. No bookmark
content is sent to an AI service.

## Updating

```sh
git pull
docker compose up -d --build
```

The extension ZIP is rebuilt from its source as part of the Docker image build.
After an extension update, replace the files in the existing unpacked-extension
directory and reload it from `chrome://extensions`.
