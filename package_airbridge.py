"""Build one user-friendly ZIP with a single AIRBridge/ root directory."""
from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path


BASE = Path(__file__).resolve().parent
EXE = BASE / "dist" / "AIRBridge.exe"
INFOGRAPHIC = BASE / "INFOGRAFIK-CARA-GUNA-AIRBRIDGE.png"
GUIDE = BASE / "PANDUAN-INFOGRAFIK.html"
START = BASE / "MULA-DI-SINI.txt"
VERSION = "v1.3"
ZIP_NAME = f"AIRBridge-{VERSION}-Pakej-Lengkap.zip"
SHARE_DIRS = [
    Path.home() / "Desktop",
    Path.home() / "Downloads",
]
SOURCES = (
    "app.py",
    "transfer_server.py",
    "make_icon.py",
    "README.md",
    "requirements.txt",
    "build.bat",
    "start.bat",
    "test_transfer.py",
    "test_ui.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for part in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def main() -> None:
    for p in (EXE, INFOGRAPHIC, GUIDE, START):
        if not p.is_file() or p.stat().st_size == 0:
            raise FileNotFoundError(f"Required package file is missing: {p}")

    # Build in the project folder first, so an interrupted copy cannot leave
    # an incomplete ZIP on Desktop or Downloads.
    destination = BASE / ZIP_NAME
    entries: list[tuple[Path, str]] = [
        (EXE, "AIRBridge/AIRBridge.exe"),
        (INFOGRAPHIC, "AIRBridge/INFOGRAFIK-CARA-GUNA.png"),
        (GUIDE, "AIRBridge/PANDUAN-INFOGRAFIK.html"),
        (START, "AIRBridge/MULA-DI-SINI.txt"),
    ]
    for relative in SOURCES:
        entries.append((BASE / relative, "AIRBridge/Kod-Sumber/" + relative))
    for folder_name in ("assets", "web"):
        for path in (BASE / folder_name).rglob("*"):
            if path.is_file():
                entries.append((
                    path, "AIRBridge/Kod-Sumber/" + path.relative_to(BASE).as_posix()
                ))

    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6,
        allowZip64=True,
    ) as archive:
        for src, target in entries:
            archive.write(src, arcname=target)

    # Test archive integrity and exact one-directory structure.
    with zipfile.ZipFile(destination, "r") as archive:
        assert archive.testzip() is None, "ZIP failed integrity check"
        members = archive.namelist()
        assert all(x.startswith("AIRBridge/") for x in members)
        assert len(members) == len(set(members))
        assert len(members) >= 12
        assert archive.getinfo("AIRBridge/AIRBridge.exe").file_size == EXE.stat().st_size
        assert archive.getinfo("AIRBridge/INFOGRAFIK-CARA-GUNA.png").file_size == INFOGRAPHIC.stat().st_size

    for directory in SHARE_DIRS:
        if directory.is_dir():
            output = directory / ZIP_NAME
            shutil.copy2(destination, output)
            assert sha256(output) == sha256(destination), "ZIP copy corrupted"
            print(f"READY: {output} ({output.stat().st_size:,} bytes)")
    print(f"EXE_SHA256: {sha256(EXE)}")
    print(f"ZIP_SHA256: {sha256(destination)}")
    print(f"FILES_IN_ZIP: {len(entries)}")


if __name__ == "__main__":
    main()
