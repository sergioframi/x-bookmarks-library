#!/usr/bin/env python3
"""Synchronize generated extension version fields from release.json."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "extension" / "xarchive"
RELEASE_PATH = EXTENSION / "release.json"


def main() -> None:
    release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    upstream = release["upstream_version"]
    revision = release["fork_revision"]
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", upstream):
        raise SystemExit("upstream_version must contain three dot-separated integers")
    if not isinstance(revision, int) or not 1 <= revision <= 65535:
        raise SystemExit("fork_revision must be an integer between 1 and 65535")

    display_version = f"{upstream}-fork.{revision}"
    chrome_version = f"{upstream}.{revision}"
    if any(int(part) > 65535 for part in chrome_version.split(".")):
        raise SystemExit("Chrome version components must not exceed 65535")

    manifest_path = EXTENSION / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = chrome_version
    manifest["version_name"] = display_version
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    version_source = f"""/** Generated release identity. Keep synchronized with release.json. */
export const UPSTREAM_VERSION = '{upstream}';
export const FORK_REVISION = {revision};
export const CHROME_VERSION = '{chrome_version}';
export const VERSION = '{display_version}';
"""
    (EXTENSION / "version.js").write_text(version_source, encoding="utf-8")

    notice = f"""# Fork notice

This distribution is an unofficial fork of
[sytelus/xarchive]({release['upstream_repository']}).

- Upstream version: `{upstream}`
- Upstream commit: `{release['upstream_commit']}`
- Fork release: `{display_version}`

The fork adds integration with a self-hosted X Bookmarks Library, including
browser-to-library pairing, direct synchronization, progress reporting, and
the supporting security and recovery behavior.

The upstream project and its contributors are the original authors of
xarchive. This fork is not affiliated with or endorsed by the upstream
project. Original copyright and license notices are retained. Modifications
made by the fork contributors are distributed under the same MIT license.

Fork repository: [{release['fork_repository']}]({release['fork_repository']}).
"""
    (EXTENSION / "NOTICE.md").write_text(notice, encoding="utf-8")
    print(f"Synchronized extension release {display_version} ({chrome_version} for Chrome)")


if __name__ == "__main__":
    main()
