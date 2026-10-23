#!/usr/bin/env python3
"""Build the downloadable extension ZIP using only the Python standard library."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED,ZipFile


ROOT=Path(__file__).resolve().parents[1]
DEFAULT_SOURCE=ROOT/"extension"/"xarchive"
DEFAULT_DESTINATION=ROOT/"app"/"assets"/"xarchive-connector.zip"
EXCLUDED_DIRECTORIES={".git",".github","docs","tests","__pycache__"}
EXCLUDED_FILES={".DS_Store","CLAUDE.md","GOAL.md","PLAN.md","FINDINGS.md","social-preview.jpeg"}


def included(path:Path,source:Path)->bool:
    relative=path.relative_to(source)
    return not any(part in EXCLUDED_DIRECTORIES for part in relative.parts) and path.name not in EXCLUDED_FILES


def build(source:Path,destination:Path)->None:
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_suffix(destination.suffix+".tmp")
    try:
        with ZipFile(temporary,"w",compression=ZIP_DEFLATED,compresslevel=9) as package:
            for path in sorted(source.rglob("*")):
                if path.is_file() and included(path,source):package.write(path,path.relative_to(source))
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=DEFAULT_SOURCE)
    parser.add_argument("--destination",type=Path,default=DEFAULT_DESTINATION)
    args=parser.parse_args()
    build(args.source.resolve(),args.destination.resolve())
    print(args.destination.resolve())


if __name__=="__main__":main()
