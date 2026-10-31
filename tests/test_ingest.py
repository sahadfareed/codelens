import io
import zipfile

import pytest

from core.ingest import load_uploads


def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    return buf.getvalue()


def test_valid_single_file():
    assert load_uploads([("a.py", b"x = 1")]) == {"a.py": "x = 1"}


def test_unsupported_type_rejected():
    with pytest.raises(ValueError, match="not a supported"):
        load_uploads([("photo.png", b"data")])


def test_empty_file_rejected():
    with pytest.raises(ValueError, match="empty"):
        load_uploads([("a.py", b"")])


def test_no_upload_rejected():
    with pytest.raises(ValueError):
        load_uploads([])


def test_corrupted_zip_rejected():
    with pytest.raises(ValueError, match="corrupted"):
        load_uploads([("bad.zip", b"not a zip")])


def test_zip_keeps_paths():
    data = make_zip({"proj/main.py": "print(1)", "proj/utils/db.py": "x = 2"})
    files = load_uploads([("proj.zip", data)])
    assert set(files) == {"proj/main.py", "proj/utils/db.py"}


def test_zip_skips_junk_and_traversal():
    data = make_zip({
        "proj/main.py": "print(1)",
        "proj/node_modules/lib.js": "x",
        "__MACOSX/proj/._main.py": "x",
        "proj/.DS_Store": "x",
        "../evil.py": "import os",
    })
    assert list(load_uploads([("p.zip", data)])) == ["proj/main.py"]


def test_zip_without_code_rejected():
    data = make_zip({"image.png": "x"})
    with pytest.raises(ValueError, match="No supported"):
        load_uploads([("p.zip", data)])
