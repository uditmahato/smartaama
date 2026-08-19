#!/usr/bin/env python3
"""
Build the SmartAama release archives.

Produces, under --out (default dist-release/):

  smartaama-backend-<version>.tar.gz   backend source (app/, alembic/, alembic.ini,
                                       requirements.txt, .env.example, start scripts,
                                       Nepal locations data) — deploy with a Python venv
  smartaama-frontend-<version>.tar.gz  production build of the React app (frontend/dist)
                                       — serve as static files behind any web server
  smartaama-<version>-full.zip         everything above + documentation/, README, LICENSE,
                                       CHANGELOG, VERSION, CONTRIBUTING
  SHA256SUMS                           checksums of the three archives

The version comes from the VERSION file at the repository root (override with --version).
The frontend must already be built (`cd frontend && npm ci && npm run build`) unless
--build is given, in which case this script runs the build itself.

Usage (from the repository root):
  python scripts/package_release.py            # package an existing frontend/dist
  python scripts/package_release.py --build    # build the frontend first
  python scripts/package_release.py --check-tag v0.1.0   # fail unless tag == v<VERSION>

Used by .github/workflows/release.yml; safe to run locally on Windows/macOS/Linux.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

# Backend: what ships. Everything not listed is intentionally left out (.venv, tests,
# uploads, *.db, caches, local .env).
BACKEND_INCLUDE = [
    "app",
    "alembic",
    "alembic.ini",
    "requirements.txt",
    ".env.example",
    "pytest.ini",
    "start_backend.bat",
    "start_backend.ps1",
    "nepal_admin_structure_province_names.json",
]
EXCLUDE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".venv", "venv", "uploads", "node_modules"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".db", ".log"}

TOP_LEVEL_DOCS = ["README.md", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", "VERSION"]


def read_version(explicit: str | None) -> str:
    if explicit:
        return explicit.strip().lstrip("v")
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _skip(path: Path) -> bool:
    if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
        return True
    return path.suffix.lower() in EXCLUDE_SUFFIXES


def _iter_files(base: Path, rel_entries: list[str]):
    """Yield (absolute_path, archive_relative_path) for the selected entries under base."""
    for entry in rel_entries:
        p = base / entry
        if not p.exists():
            print(f"  warning: {p.relative_to(ROOT)} missing, skipped", file=sys.stderr)
            continue
        if p.is_file():
            if not _skip(p):
                yield p, Path(entry)
            continue
        for f in sorted(p.rglob("*")):
            if f.is_file() and not _skip(f.relative_to(base)):
                yield f, f.relative_to(base)


def build_frontend() -> None:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    print("Building frontend (npm ci && npm run build)...")
    subprocess.run([npm, "ci"], cwd=FRONTEND, check=True)
    subprocess.run([npm, "run", "build"], cwd=FRONTEND, check=True)


def make_tar(out: Path, root_name: str, files, extra_text: dict[str, str] | None = None) -> int:
    """Write a gzip tarball; `extra_text` adds generated files ({archive-relative path: content})."""
    import io
    import time

    count = 0
    with tarfile.open(out, "w:gz") as tar:
        for abs_path, rel in files:
            info = tar.gettarinfo(str(abs_path), arcname=f"{root_name}/{rel.as_posix()}")
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            with open(abs_path, "rb") as fh:
                tar.addfile(info, fh)
            count += 1
        for rel, text in (extra_text or {}).items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(name=f"{root_name}/{rel}")
            info.size = len(data)
            info.mtime = int(time.time())
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
            count += 1
    return count


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "dist-release"), help="output directory (default dist-release/)")
    ap.add_argument("--version", help="override VERSION file")
    ap.add_argument("--build", action="store_true", help="run the frontend production build first")
    ap.add_argument("--frontend-dist", default=str(FRONTEND / "dist"), help="path of the built frontend")
    ap.add_argument("--check-tag", help="fail unless this git tag equals v<version> (used by CI)")
    args = ap.parse_args()

    version = read_version(args.version)
    if args.check_tag and args.check_tag.strip() != f"v{version}":
        print(f"error: tag {args.check_tag!r} does not match VERSION file (v{version})", file=sys.stderr)
        return 2

    if args.build:
        build_frontend()
    dist = Path(args.frontend_dist)
    if not (dist / "index.html").is_file():
        print(f"error: frontend build not found at {dist} (run with --build or `npm run build` first)", file=sys.stderr)
        return 2

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    print(f"Packaging SmartAama {version} -> {out}")

    # The API reads VERSION from the repo root or from backend/VERSION; the backend-only
    # archive gets a copy so `app.version` is correct when deployed on its own.
    backend_tar = out / f"smartaama-backend-{version}.tar.gz"
    n = make_tar(
        backend_tar,
        f"smartaama-backend-{version}",
        _iter_files(BACKEND, BACKEND_INCLUDE),
        extra_text={"VERSION": version + "\n"},
    )
    print(f"  {backend_tar.name}: {n} files")

    frontend_tar = out / f"smartaama-frontend-{version}.tar.gz"
    n = make_tar(frontend_tar, f"smartaama-frontend-{version}", ((f, f.relative_to(dist)) for f in sorted(dist.rglob("*")) if f.is_file()))
    print(f"  {frontend_tar.name}: {n} files")

    full_zip = out / f"smartaama-{version}-full.zip"
    with zipfile.ZipFile(full_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        top = f"smartaama-{version}"
        for abs_path, rel in _iter_files(BACKEND, BACKEND_INCLUDE):
            z.write(abs_path, f"{top}/backend/{rel.as_posix()}")
        z.writestr(f"{top}/backend/VERSION", version + "\n")
        for f in sorted(dist.rglob("*")):
            if f.is_file():
                z.write(f, f"{top}/frontend-dist/{f.relative_to(dist).as_posix()}")
        for f in sorted((ROOT / "documentation").rglob("*")):
            if f.is_file() and not _skip(f):
                z.write(f, f"{top}/documentation/{f.relative_to(ROOT / 'documentation').as_posix()}")
        for name in TOP_LEVEL_DOCS:
            p = ROOT / name
            if p.is_file():
                z.write(p, f"{top}/{name}")
    print(f"  {full_zip.name}")

    sums = out / "SHA256SUMS"
    with open(sums, "w", encoding="utf-8", newline="\n") as fh:
        for f in (backend_tar, frontend_tar, full_zip):
            fh.write(f"{sha256(f)}  {f.name}\n")
    print(f"  {sums.name}")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
