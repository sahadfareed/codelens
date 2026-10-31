import io
import zipfile

ALLOWED_EXT = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
    ".cs", ".go", ".rb", ".php", ".html", ".css", ".json", ".md",
    ".txt", ".yml", ".yaml", ".toml", ".sql", ".sh",
}
SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__",
             "dist", "build", "__MACOSX", ".idea", ".vscode"}
SKIP_FILES = {".DS_Store", "package-lock.json", "yarn.lock"}

MAX_FILE_SIZE = 1_000_000      # 1 MB per file
MAX_ZIP_SIZE = 10_000_000      # 10 MB per ZIP
MAX_FILES = 200


def get_ext(name: str) -> str:
    return "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""


def load_single(name: str, data: bytes) -> dict[str, str]:
    if get_ext(name) not in ALLOWED_EXT:
        raise ValueError(f"'{name}' is not a supported file type.")
    if len(data) == 0:
        raise ValueError(f"'{name}' is empty.")
    if len(data) > MAX_FILE_SIZE:
        raise ValueError(f"'{name}' is larger than 1 MB.")
    text = data.decode("utf-8", errors="replace")
    if not text.strip():
        raise ValueError(f"'{name}' contains only whitespace.")
    return {name: text}


def load_zip(name: str, data: bytes) -> dict[str, str]:
    if len(data) > MAX_ZIP_SIZE:
        raise ValueError(f"'{name}' is larger than 10 MB.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError(f"'{name}' is corrupted or not a valid ZIP file.")

    files = {}
    for info in zf.infolist():
        path = info.filename
        parts = path.split("/")
        # security: block path traversal, never extract to disk
        if info.is_dir() or ".." in parts or path.startswith("/"):
            continue
        if any(p in SKIP_DIRS for p in parts) or parts[-1] in SKIP_FILES:
            continue
        if get_ext(path) not in ALLOWED_EXT or info.file_size > MAX_FILE_SIZE:
            continue
        text = zf.read(info).decode("utf-8", errors="replace")
        if text.strip():
            files[path] = text
        if len(files) >= MAX_FILES:
            break

    if not files:
        raise ValueError(f"No supported source files found in '{name}'.")
    return files


def load_uploads(uploads) -> dict[str, str]:
    """uploads = list of (filename, bytes). Returns {path: code}."""
    if not uploads:
        raise ValueError("Please upload at least one file.")
    all_files = {}
    for name, data in uploads:
        if get_ext(name) == ".zip":
            all_files.update(load_zip(name, data))
        else:
            all_files.update(load_single(name, data))
    return all_files