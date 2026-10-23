# Release verification

Before publishing a source release:

1. Run the Python and extension regression suites.
2. Build from a clean checkout with no `.env`, database, model cache, or user.
3. Confirm that `docker compose up -d --build` exposes host port `8080`.
4. Confirm that an optional `.env` changes only the host port.
5. Complete account creation, extension download, pairing, and a full import.
6. Verify local embedding progress, category review, and category confirmation.
7. Restart the service and verify that the account, bookmarks, model, and
   categories remain in the named volumes.
8. Run `scripts/backup.sh` and validate the resulting SQLite backup.
9. Review the source tree for `.env`, databases, archives, logs, model files,
   credentials, private hostnames, IP addresses, and personal account data.

The currently verified reference target is a 64-bit Raspberry Pi running
Debian with 4 GB of RAM. Other Linux ARM64 and AMD64 hosts are expected to work
through the multi-architecture Python base image but require separate release
verification before being advertised as supported.
