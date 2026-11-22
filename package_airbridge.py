"""Build a user-only Windows ZIP. Never include application source files."""
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
VERSION = "v1.6"
ZIP_NAME = f"AIRBridge-{VERSION}-Windows.zip"
SHARE_DIRS = [
    Path.home() / "Desktop",
    Path.home() / "Downloads",
]
PACKAGE_FILES = (
    (EXE, "AIRBridge/AIRBridge.exe"),
    (BASE / "START_HERE.txt", "AIRBridge/START_HERE.txt"),
    (BASE / "GUIDE_EN.md", "AIRBridge/GUIDE_EN.md"),
    (BASE / "AIRBridge-Guide-EN.png", "AIRBridge/AIRBridge-Guide-EN.png"),
    (BASE / "GUIDE_BM.md", "AIRBridge/Optional-Bahasa-Melayu/GUIDE_BM.md"),
    (BASE / "AIRBridge-Guide-BM.png", "AIRBridge/Optional-Bahasa-Melayu/Guide-BM.png"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for part in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def main() -> None:
    for p, _ in PACKAGE_FILES:
        if not p.is_file() or p.stat().st_size == 0:
            raise FileNotFoundError(f"Required package file is missing: {p}")

    # Build in the project folder first, so an interrupted copy cannot leave
    # an incomplete ZIP on Desktop or Downloads.
    destination = BASE / ZIP_NAME
    entries = PACKAGE_FILES

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
        assert len(members) == len(PACKAGE_FILES)
        assert archive.getinfo("AIRBridge/AIRBridge.exe").file_size == EXE.stat().st_size
        assert set(members) == {name for _, name in PACKAGE_FILES}
        assert all(not name.lower().endswith((".py", ".js", ".bat", ".html", ".spec", ".pyc")) for name in members)
        assert all("source" not in name.lower() and "kod-sumber" not in name.lower() for name in members)

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
