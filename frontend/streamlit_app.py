import os
import time
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
PUBLIC_BACKEND_URL = os.getenv("PUBLIC_BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Book Reader", layout="wide")

st.markdown(
    """
    <style>
    .summary-box {
        border: 1px solid #ddd;
        padding: 12px;
        border-radius: 8px;
        max-height: 420px;
        overflow-y: auto;
        background: #fafafa;
    }
    .section-title {
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path, params=None):
    try:
        return requests.get(f"{BACKEND_URL}{path}", params=params, timeout=10)
    except requests.RequestException:
        return None


def api_post(path, files=None, json=None, params=None):
    try:
        return requests.post(f"{BACKEND_URL}{path}", files=files, json=json, params=params, timeout=30)
    except requests.RequestException:
        return None


def api_put(path, json=None):
    try:
        return requests.put(f"{BACKEND_URL}{path}", json=json, timeout=10)
    except requests.RequestException:
        return None


def api_delete(path):
    try:
        return requests.delete(f"{BACKEND_URL}{path}", timeout=10)
    except requests.RequestException:
        return None


def fetch_audio(version_id: int):
    try:
        resp = requests.get(f"{BACKEND_URL}/summary_versions/{version_id}/audio", timeout=30)
        if resp.status_code != 200:
            return None, None
        content_type = resp.headers.get("Content-Type", "audio/mpeg")
        return resp.content, content_type
    except requests.RequestException:
        return None, None


def poll_job(job_id, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        res = api_get(f"/jobs/{job_id}")
        if res and res.status_code == 200:
            data = res.json()
            if data.get("status") in {"finished", "failed"}:
                return data
        time.sleep(1)
    return {"status": "timeout"}


def render_tree(nodes, on_click, level=0):
    for node in nodes:
        prefix = "· " * level
        label = f"{prefix}{node['title']} (p{node['page_start']}-{node['page_end']})"
        if st.button(label, key=f"section_{node['id']}"):
            on_click(node)
        if node.get("children"):
            expanded = st.checkbox("Show subsections", key=f"expand_{node['id']}")
            if expanded:
                render_tree(node["children"], on_click, level=level + 1)


def render_tree_explorer(nodes, on_click, level=0):
    for node in nodes:
        prefix = "· " * level
        label = f"{prefix}{node['title']}"
        if st.button(label, key=f"explorer_{node['id']}"):
            on_click(node)
        if node.get("children"):
            expanded = st.checkbox("Show subsections", key=f"explorer_expand_{node['id']}")
            if expanded:
                render_tree_explorer(node["children"], on_click, level=level + 1)


def summary_dialog(section, recursive):
    st.session_state["overview_only"] = None
    state_key = f"selected_version_{section['id']}"

    def render_dialog_body():
        st.write(f"Pages {section['page_start']} - {section['page_end']}")
        versions_response = api_get(f"/sections/{section['id']}/summary_versions")
        if not versions_response:
            st.error("Backend unavailable.")
            return
        versions = versions_response.json()
        version_ids = [v["id"] for v in versions]
        labels = [f"v{v['version_number']}" for v in versions]

        selected_version_id = st.session_state.get(state_key)
        if labels:
            default_index = 0
            if selected_version_id in version_ids:
                default_index = version_ids.index(selected_version_id)
            selected_label = st.selectbox("Versions", labels, index=default_index)
            selected_version_id = version_ids[labels.index(selected_label)]
            st.session_state[state_key] = selected_version_id

        cols = st.columns(3)
        if cols[0].button("Regenerate"):
            res = api_post(
                f"/sections/{section['id']}/summaries:generate",
                params={"recursive": str(recursive).lower()},
            )
            if not res:
                st.error("Backend unavailable.")
                return
            job_id = res.json().get("job_id")
            with st.spinner("Generating summary..."):
                result = poll_job(job_id, timeout=120)
            if result.get("result"):
                if isinstance(result["result"], dict):
                    st.session_state["overview_only"] = result["result"].get("overview")
                    st.warning(result["result"].get("warning"))
                else:
                    selected_version_id = result["result"]
                    st.session_state[state_key] = selected_version_id
                    versions_response = api_get(f"/sections/{section['id']}/summary_versions")
                    versions = versions_response.json() if versions_response else []
                    version_ids = [v["id"] for v in versions]
                    labels = [f"v{v['version_number']}" for v in versions]
        if cols[1].button("Delete") and selected_version_id:
            api_delete(f"/summary_versions/{selected_version_id}")
            versions_response = api_get(f"/sections/{section['id']}/summary_versions")
            versions = versions_response.json() if versions_response else []
            version_ids = [v["id"] for v in versions]
            labels = [f"v{v['version_number']}" for v in versions]
            selected_version_id = version_ids[0] if version_ids else None
            st.session_state[state_key] = selected_version_id
        if cols[2].button("Listen") and selected_version_id:
            res = api_post(f"/summary_versions/{selected_version_id}/tts")
            if not res:
                st.error("Backend unavailable.")
                return
            job_id = res.json().get("job_id")
            with st.spinner("Generating audio..."):
                poll_job(job_id, timeout=120)
            audio_bytes, content_type = fetch_audio(selected_version_id)
            if not audio_bytes:
                st.error("Audio not available. Check TTS settings.")
                return
            st.audio(audio_bytes, format=content_type)

        content = None
        if st.session_state.get("overview_only"):
            content = st.session_state["overview_only"]
        elif selected_version_id:
            version_response = api_get(f"/summary_versions/{selected_version_id}")
            if version_response:
                version = version_response.json()
                content = version.get("content")
        elif st.session_state.get(state_key):
            version_response = api_get(f"/summary_versions/{st.session_state[state_key]}")
            if version_response:
                version = version_response.json()
                content = version.get("content")

        if content:
            st.text_area("Summary", content, height=320, disabled=True)
        else:
            st.info("No summary available yet. Click Regenerate to create one.")

        assets_response = api_get(
            f"/sections/{section['id']}/assets", params={"recursive": str(recursive).lower()}
        )
        assets = assets_response.json() if assets_response else []
        if assets:
            st.subheader("Figures")
            for asset in assets:
                image_url = f"{PUBLIC_BACKEND_URL}/assets/{asset['id']}"
                st.image(image_url, caption=asset.get("caption"))

    if hasattr(st, "dialog"):
        with st.dialog(f"Summary: {section['title']}"):
            render_dialog_body()
    elif hasattr(st, "experimental_dialog"):
        @st.experimental_dialog(f"Summary: {section['title']}")
        def _dialog():
            render_dialog_body()
        _dialog()
    else:
        st.subheader(f"Summary: {section['title']}")
        render_dialog_body()


st.sidebar.title("AI Book Reader")

uploaded = st.sidebar.file_uploader("Upload PDF", type=["pdf"])
if uploaded:
    file_bytes = uploaded.getvalue()
    upload_id = f"{uploaded.name}:{len(file_bytes)}"
    if st.session_state.get("last_upload_id") != upload_id:
        res = api_post("/books", files={"file": (uploaded.name, file_bytes, "application/pdf")})
        if res and res.status_code == 200:
            st.sidebar.success("Upload successful. Ingestion started.")
            st.session_state["last_upload_id"] = upload_id
        else:
            st.sidebar.error("Upload failed. Backend unavailable.")

if "books_cache" not in st.session_state:
    st.session_state["books_cache"] = []
books_response = api_get("/books")
if books_response and books_response.status_code == 200:
    st.session_state["books_cache"] = books_response.json()
books = st.session_state["books_cache"]
book_options = {f"{b['id']} - {b['title']}": b for b in books}
selected_label = st.sidebar.selectbox("Select Book", ["None"] + list(book_options.keys()))

if selected_label != "None":
    book = book_options[selected_label]
    progress = api_get(f"/books/{book['id']}/progress")
    last_page = progress.json().get("last_page", 1) if progress and progress.status_code == 200 else 1
    if st.session_state.get("current_book_id") != book["id"]:
        st.session_state["current_book_id"] = book["id"]
        st.session_state["page"] = int(last_page)

    tabs = st.tabs(["Reader", "Summaries Explorer"])

    with tabs[0]:
        left, right = st.columns([1, 2])
        with left:
            st.subheader("Sections")
            tree_response = api_get(f"/books/{book['id']}/sections")
            tree = tree_response.json() if tree_response else []
            recursive = st.checkbox("Recursive summary", value=True)

            def on_section_click(node):
                st.session_state["selected_section"] = node
                st.session_state["show_summary"] = True
                st.session_state["page"] = int(node["page_start"])

            render_tree(tree, on_section_click)

        with right:
            st.subheader("PDF Viewer")
            page = st.number_input("Page", min_value=1, step=1, key="page")
            api_put(f"/books/{book['id']}/progress", json={"last_page": int(page), "last_section_id": None})
            pdf_url = f"{PUBLIC_BACKEND_URL}/books/{book['id']}/pdf#page={page}"
            st.markdown(
                f"<iframe src='{pdf_url}' width='100%' height='800px' style='border:0;'></iframe>",
                unsafe_allow_html=True,
            )

        if st.session_state.get("show_summary") and st.session_state.get("selected_section"):
            summary_dialog(st.session_state["selected_section"], recursive)
            st.session_state["show_summary"] = False

    with tabs[1]:
        st.subheader("Summaries Explorer")
        tree_response = api_get(f"/books/{book['id']}/sections")
        tree = tree_response.json() if tree_response else []

        def on_explorer_click(node):
            st.session_state["selected_section"] = node
            st.session_state["show_summary"] = True

        render_tree_explorer(tree, on_explorer_click)

        if st.session_state.get("show_summary") and st.session_state.get("selected_section"):
            summary_dialog(st.session_state["selected_section"], True)
            st.session_state["show_summary"] = False
else:
    st.info("Upload a PDF and select a book to begin.")
