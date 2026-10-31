from core.analyzer import analyze


def test_detects_functions_and_classes():
    code_map, _, _ = analyze({"m.py": "class A:\n    def go(self, x): pass\n\ndef helper(y): pass\n"})
    assert "class A" in code_map
    assert "go(x)" in code_map
    assert "helper(y)" in code_map


def test_detects_internal_relationship():
    files = {"main.py": "from storage import Store\n", "storage.py": "class Store: pass\n"}
    code_map, _, _ = analyze(files)
    assert "main.py -> storage.py" in code_map


def test_syntax_error_does_not_crash():
    code_map, _, _ = analyze({"bad.py": "x = ("})
    assert "syntax error" in code_map


def test_dependencies_from_requirements():
    code_map, _, _ = analyze({"app.py": "import flask\n", "requirements.txt": "flask==3.0\n"})
    assert "flask" in code_map


def test_javascript_functions_detected():
    code_map, _, _ = analyze({"app.js": "function start() {}\nconst stop = () => {};\n"})
    assert "start()" in code_map and "stop()" in code_map


def test_large_file_truncated():
    _, selected, notes = analyze({"big.py": "x = 1\n" * 20000})
    assert "[TRUNCATED]" in selected["big.py"]
    assert notes
