import ast
import json
import re
import sys
from pathlib import PurePosixPath

from core.ingest import get_ext

MAX_TOTAL_CHARS = 150_000      # total code sent to the LLM
MAX_CHARS_PER_FILE = 30_000
STDLIB = set(sys.stdlib_module_names)

CODE_EXT = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
            ".cs", ".go", ".rb", ".php", ".sql", ".sh"}
LANGUAGES = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
             ".jsx": "JavaScript (React)", ".tsx": "TypeScript (React)",
             ".java": "Java", ".c": "C", ".cpp": "C++", ".h": "C/C++ Header",
             ".cs": "C#", ".go": "Go", ".rb": "Ruby", ".php": "PHP",
             ".sql": "SQL", ".sh": "Shell"}

# Regex patterns for non-Python languages
FUNC_RE = re.compile(
    r"function\s+(\w+)\s*\("                                   # JS function
    r"|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>"  # arrow fn
    r"|\bfunc\s+(?:\([^)]*\)\s*)?(\w+)\s*\("                    # Go
    r"|\bdef\s+(\w+)"                                           # Ruby
    r"|(?:public|private|protected|static)[\w<>\[\]\s]*\s(\w+)\s*\([^)]*\)\s*\{"  # Java/C#
)
CLASS_RE = re.compile(r"\b(?:class|interface|struct)\s+(\w+)")
IMPORT_RE = re.compile(
    r"""from\s+['"]([^'"]+)['"]"""              # JS: import x from 'y'
    r"""|require\(\s*['"]([^'"]+)['"]\s*\)"""   # JS: require('y')
    r"""|^\s*import\s+(?:static\s+)?([\w.*]+)\s*;"""  # Java
    r"""|^\s*import\s+"([^"]+)\""""             # Go
    r"""|#include\s*[<"]([^>"]+)[>"]""",        # C/C++
    re.M,
)
ERROR_RE = re.compile(r"\b(try|catch|except|throw|raise)\b")
ENTRY_RE = re.compile(r"public\s+static\s+void\s+main|\bfunc\s+main\s*\(|\.listen\s*\(|int\s+main\s*\(")


# ---------- Python analysis (AST, no execution) ----------

def _doc(node):
    d = ast.get_docstring(node)
    return d.strip().splitlines()[0] if d else ""


def _fn_sig(fn):
    args = [a.arg for a in fn.args.args if a.arg not in ("self", "cls")]
    sig = f"{fn.name}({', '.join(args)})"
    if fn.returns is not None:
        sig += f" -> {ast.unparse(fn.returns)}"
    doc = _doc(fn)
    return sig + (f"  # {doc}" if doc else "")


def analyze_python(path, src):
    info = {"path": path, "language": "Python", "imports": [], "classes": [],
            "functions": [], "entry_point": False, "error_handling": 0}
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        info["error"] = f"Could not parse (syntax error at line {e.lineno})"
        return info

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            info["imports"] += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mod = "." * node.level + (node.module or "")
            info["imports"].append(mod)
            info["imports"] += [f"{mod}.{a.name}" for a in node.names]
        elif isinstance(node, (ast.Try, ast.Raise)):
            info["error_handling"] += 1

    for node in tree.body:   # top level only, keeps structure clean
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info["functions"].append(_fn_sig(node))
        elif isinstance(node, ast.ClassDef):
            methods = [_fn_sig(n) for n in node.body
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            info["classes"].append({"name": node.name, "doc": _doc(node), "methods": methods})
        elif isinstance(node, ast.If) and "__main__" in ast.unparse(node.test):
            info["entry_point"] = True
    return info


# ---------- Other languages (regex) ----------

def analyze_generic(path, src):
    ext = get_ext(path)
    funcs = []
    for m in FUNC_RE.finditer(src):
        name = next(g for g in m.groups() if g)
        if name not in ("if", "for", "while", "switch", "catch") and name not in funcs:
            funcs.append(name + "()")
    imports = [next(g for g in m.groups() if g) for m in IMPORT_RE.finditer(src)]
    return {
        "path": path,
        "language": LANGUAGES.get(ext, ext),
        "imports": imports,
        "classes": [{"name": c, "doc": "", "methods": []} for c in dict.fromkeys(CLASS_RE.findall(src))],
        "functions": funcs,
        "entry_point": bool(ENTRY_RE.search(src)),
        "error_handling": len(ERROR_RE.findall(src)),
    }


# ---------- Project-level analysis ----------

def build_file_tree(paths):
    tree = {}
    for p in sorted(paths):
        node = tree
        for part in p.split("/"):
            node = node.setdefault(part, {})
    lines = []

    def walk(node, depth):
        for name in sorted(node, key=lambda n: (not node[n], n)):  # folders first
            lines.append("  " * depth + (name + "/" if node[name] else name))
            walk(node[name], depth + 1)

    walk(tree, 0)
    return "\n".join(lines)


def detect_dependencies(files, analyses):
    deps = {}
    for path, src in files.items():
        name = PurePosixPath(path).name
        if name == "requirements.txt":
            for line in src.splitlines():
                line = line.strip()
                if line and not line.startswith(("#", "-")):
                    deps[re.split(r"[=<>!~\[; ]", line)[0]] = "requirements.txt"
        elif name == "package.json":
            try:
                data = json.loads(src)
                for section in ("dependencies", "devDependencies"):
                    for pkg in data.get(section, {}):
                        deps[pkg] = f"package.json ({section})"
            except json.JSONDecodeError:
                pass

    local = {part for p in files for part in PurePosixPath(p).with_suffix("").parts}
    for a in analyses:
        if a["language"] == "Python":
            for imp in a["imports"]:
                top = imp.split(".")[0]
                if top and top not in STDLIB and top not in local and top not in deps:
                    deps[top] = f"imported in {a['path']}"
    return deps


def find_relationships(files, analyses):
    stems = {}
    for p in files:
        if get_ext(p) in CODE_EXT:
            stems.setdefault(PurePosixPath(p).stem, p)
    rels = set()
    for a in analyses:
        for imp in a["imports"]:
            cleaned = re.sub(r"\.(py|js|ts|jsx|tsx|java|go|h)$", "", imp)
            name = re.split(r"[./\\]", cleaned)[-1]
            target = stems.get(name)
            if target and target != a["path"]:
                rels.add(f"{a['path']} -> {target}")
    return sorted(rels)


def prepare_files(files):
    """Pick which file contents go to the LLM, within the size budget."""
    order = sorted(files, key=lambda p: (get_ext(p) not in CODE_EXT, p.count("/"), p))
    selected, notes, used = {}, [], 0
    for p in order:
        src = files[p]
        remaining = MAX_TOTAL_CHARS - used
        if remaining <= 500:
            notes.append(f"{p}: omitted (size limit reached)")
            continue
        limit = min(MAX_CHARS_PER_FILE, remaining)
        if len(src) > limit:
            src = src[:limit] + "\n... [TRUNCATED]"
            notes.append(f"{p}: truncated to first {limit} characters")
        selected[p] = src
        used += len(src)
    return selected, notes


def format_code_map(files, analyses, deps, rels, notes):
    out = [f"TOTAL FILES: {len(files)}", "", "FILE TREE:", build_file_tree(files), "",
           "PER-FILE STRUCTURE:"]
    for a in analyses:
        out.append(f"\n[{a['path']}] ({a['language']})")
        if a.get("error"):
            out.append(f"  ! {a['error']}")
        if a["entry_point"]:
            out.append("  * Entry point detected")
        if a["imports"]:
            out.append("  imports: " + ", ".join(dict.fromkeys(a["imports"])))
        for c in a["classes"]:
            out.append(f"  class {c['name']}" + (f"  # {c['doc']}" if c["doc"] else ""))
            for m in c["methods"]:
                out.append(f"    method {m}")
        for f in a["functions"]:
            out.append(f"  function {f}")
        if a["error_handling"]:
            out.append(f"  error-handling statements: {a['error_handling']}")

    out.append("\nINTERNAL RELATIONSHIPS (file -> file it imports):")
    out += [f"  {r}" for r in rels] or ["  None detected"]
    out.append("\nDETECTED DEPENDENCIES:")
    out += [f"  {k}  ({v})" for k, v in deps.items()] or ["  None detected"]
    if notes:
        out.append("\nANALYSIS COVERAGE NOTES:")
        out += [f"  {n}" for n in notes]
    return "\n".join(out)


def analyze(files: dict[str, str]):
    """Returns (code_map, files_for_llm, coverage_notes)."""
    analyses = []
    for path, src in files.items():
        ext = get_ext(path)
        if ext == ".py":
            analyses.append(analyze_python(path, src))
        elif ext in CODE_EXT:
            analyses.append(analyze_generic(path, src))
    deps = detect_dependencies(files, analyses)
    rels = find_relationships(files, analyses)
    selected, notes = prepare_files(files)
    code_map = format_code_map(files, analyses, deps, rels, notes)
    return code_map, selected, notes