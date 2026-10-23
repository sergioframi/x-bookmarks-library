"""Create an optional local .env file with the documented defaults."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


root=Path(__file__).resolve().parent.parent
source=root/".env.example"
destination=root/".env"
if destination.exists():raise SystemExit(".env already exists; it was not overwritten")
shutil.copyfile(source,destination)
os.chmod(destination,0o600)
print("Created .env with PORT=8080. Edit PORT before starting if needed.")
