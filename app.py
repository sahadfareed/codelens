import streamlit as st

from core.analyzer import analyze
from core.exporter import to_docx, to_markdown
from core.ingest import load_uploads
from core.llm import generate_docs

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

st.set_page_config(page_title="CodeLens", page_icon="🔍", layout="wide")
st.title("🔍 CodeLens")
st.caption("AI-powered code explanation and documentation generator")

for key in ("files", "code_map", "selected", "notes", "doc", "project"):
    st.session_state.setdefault(key, None)


def run_generation():
    with st.spinner("Generating documentation with AI... this can take 15–60 seconds"):
        st.session_state.doc = generate_docs(st.session_state.code_map, st.session_state.selected, st.session_state.project)


left, right = st.columns([1, 2], gap="large")

# ---------------- Panel A: Upload & Analyse ----------------
with left:
    st.subheader("1 · Upload & Analyse")
    uploads = st.file_uploader(
        "Upload source files or a .zip project",
        accept_multiple_files=True,
        help="Supported: .py .js .ts .java .c .cpp .go .html .css .json .md and more, or a .zip of a project.",
    )

    if uploads:
        st.markdown("**Selected:**")
        for u in uploads:
            st.write(f"📄 {u.name}  ({u.size / 1024:.1f} KB)")

    if st.button("Analyse Code", type="primary", disabled=not uploads, width="stretch"):
        st.session_state.doc = None
        try:
            with st.spinner("Reading and validating files..."):
                files = load_uploads([(u.name, u.getvalue()) for u in uploads])
            with st.spinner("Analysing code structure..."):
                code_map, selected, notes = analyze(files)
            project = uploads[0].name.rsplit(".", 1)[0] if len(uploads) == 1 else "project"
            st.session_state.update(files=files, code_map=code_map, selected=selected,
                                    notes=notes, project=project)
            run_generation()
        except (ValueError, RuntimeError) as e:
            st.error(f"⚠️ {e}")

    if st.session_state.files:
        st.success(f"✅ {len(st.session_state.files)} file(s) analysed")
        for note in st.session_state.notes or []:
            st.warning(note)
        with st.expander("Files analysed"):
            for path in st.session_state.files:
                st.write(f"`{path}`")
        with st.expander("Code map (static analysis)"):
            st.code(st.session_state.code_map, language="text")

# ---------------- Panel B: Generated Documentation ----------------
with right:
    st.subheader("2 · Generated Documentation")
    doc = st.session_state.doc

    if doc:
        name = st.session_state.project or "documentation"
        c1, c2, c3 = st.columns(3)
        c1.download_button("⬇️ Markdown (.md)", to_markdown(doc), f"{name}_docs.md",
                           "text/markdown", width="stretch")
        c2.download_button("⬇️ Word (.docx)", to_docx(doc), f"{name}_docs.docx",
                           DOCX_MIME, width="stretch")
        if c3.button("🔄 Regenerate", width="stretch"):
            try:
                run_generation()
                st.rerun()
            except RuntimeError as e:
                st.error(f"⚠️ {e}")
        with st.container(height=700, border=True):
            st.markdown(doc)

    elif st.session_state.code_map:
        st.warning("Code was analysed, but documentation could not be generated.")
        if st.button("🔄 Try again", type="primary"):
            try:
                run_generation()
                st.rerun()
            except RuntimeError as e:
                st.error(f"⚠️ {e}")
    else:
        st.info("Upload code on the left and click **Analyse Code** to generate documentation.")
