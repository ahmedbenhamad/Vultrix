import os
import sys
import zipfile
import tarfile
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ANSI Colors
C = "\033[96m"
G = "\033[92m"
Y = "\033[93m"
R = "\033[91m"
RESET = "\033[0m"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Extensions that are completely useless for a RAG knowledge base
JUNK_EXTENSIONS = {
    # Binaries & Executables
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".obj", ".class",
    ".pyc", ".pyo", ".pyd", ".whl", ".egg",
    # Media (non-OCR-able or too heavy)
    ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".wav", ".flac",
    ".gif", ".ico", ".svg", ".webp", ".webm",
    # Packages
    ".jar", ".war", ".deb", ".rpm", ".msi", ".apk", ".ipa",
    ".nupkg", ".cab",
    # Database dumps
    ".dump", ".bak",
    # Fonts
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    # Debug / Compiled symbols
    ".pdb", ".lib", ".sdb", ".raw", ".ddNSi",
    # Windows attack payloads (binary, not readable text)
    ".sct", ".hta", ".inf", ".cpl", ".chm", ".xll", ".wll",
    ".lnk", ".dotm", ".xlam", ".ppam", ".vib", ".SED",
    # macOS specific
    ".plist",
    # Misc
    ".iso", ".vmdk", ".ova", ".lock", ".DS_Store",
}

ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar"}

JUNK_DIRS = {
    "__pycache__", ".git", ".github", ".svn", "node_modules",
    ".vscode", ".idea", ".eggs", "dist", "build",
    "__MACOSX", ".tox", ".mypy_cache", ".pytest_cache",
}


def extract_archive(archive_path):
    """Extract a single archive and delete it."""
    try:
        target_dir = archive_path.with_suffix("")
        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(target_dir)
        elif archive_path.suffix in {".tar", ".gz", ".tgz", ".bz2", ".xz"}:
            with tarfile.open(archive_path, 'r:*') as tf:
                tf.extractall(target_dir, filter='data')
        archive_path.unlink()
        return archive_path, True
    except Exception:
        return archive_path, False


def main():
    if not DATA_DIR.exists():
        print(f"{R}[!] Data directory not found: {DATA_DIR}{RESET}")
        sys.exit(1)

    print(f"\n{Y}{'='*60}")
    print(f"  DATA CLEANER - Preparing data/ for RAG Ingestion")
    print(f"{'='*60}{RESET}\n")

    # === SINGLE PASS: Walk the tree once, classify everything ===
    print(f"{G}[*] Scanning data/ directory...{RESET}")
    
    junk_dirs_found = []
    junk_files_found = []
    archives_found = []
    
    for dirpath, dirnames, filenames in os.walk(str(DATA_DIR), topdown=True):
        # Prune junk directories immediately so os.walk skips them entirely
        pruned = []
        for d in dirnames:
            if d in JUNK_DIRS:
                junk_dirs_found.append(os.path.join(dirpath, d))
            else:
                pruned.append(d)
        dirnames[:] = pruned  # Modify in-place to skip these subtrees
        
        for f in filenames:
            filepath = os.path.join(dirpath, f)
            ext = os.path.splitext(f)[1].lower()
            if ext in ARCHIVE_EXTENSIONS:
                archives_found.append(Path(filepath))
            elif ext in JUNK_EXTENSIONS:
                junk_files_found.append(filepath)

    print(f"  Found: {len(archives_found)} archives, {len(junk_dirs_found)} junk dirs, {len(junk_files_found)} junk files\n")

    # === Phase 1: Extract archives (parallel) ===
    extracted = 0
    if archives_found:
        print(f"{G}[Phase 1] Extracting {len(archives_found)} archive(s)...{RESET}")
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(extract_archive, a): a for a in archives_found}
            for future in as_completed(futures):
                path, success = future.result()
                if success:
                    extracted += 1
        print(f"  Extracted {extracted} archive(s).\n")

    # === Phase 2: Remove junk directories ===
    if junk_dirs_found:
        print(f"{G}[Phase 2] Removing {len(junk_dirs_found)} junk directory tree(s)...{RESET}")
        for d in junk_dirs_found:
            shutil.rmtree(d, ignore_errors=True)
        print(f"  Done.\n")

    # === Phase 3: Delete junk files (parallel) ===
    freed = 0
    if junk_files_found:
        print(f"{G}[Phase 3] Removing {len(junk_files_found)} junk file(s)...{RESET}")
        for fp in junk_files_found:
            try:
                freed += os.path.getsize(fp)
                os.remove(fp)
            except OSError:
                pass
        print(f"  Freed {freed / (1024*1024):.1f} MB.\n")

    # === Phase 4: Prune empty directories ===
    print(f"{G}[Phase 4] Pruning empty directories...{RESET}")
    empty_removed = 0
    for dirpath, dirnames, filenames in os.walk(str(DATA_DIR), topdown=False):
        if not os.listdir(dirpath):
            try:
                os.rmdir(dirpath)
                empty_removed += 1
            except OSError:
                pass
    print(f"  Removed {empty_removed} empty folder(s).\n")

    # === Summary ===
    print(f"{Y}{'='*60}")
    print(f"  CLEANUP COMPLETE")
    print(f"  Archives extracted: {extracted}")
    print(f"  Junk dirs removed:  {len(junk_dirs_found)}")
    print(f"  Junk files removed: {len(junk_files_found)}")
    print(f"  Space freed:        {freed / (1024*1024):.1f} MB")
    print(f"{'='*60}{RESET}")
    print(f"\n{G}Your data/ folder is now clean and ready for ingestion!{RESET}")


if __name__ == "__main__":
    main()
