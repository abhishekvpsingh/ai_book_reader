import os
import time
import base64
import requests
import streamlit as st
from streamlit.components.v1 import html as components_html
from streamlit_autorefresh import st_autorefresh

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
PUBLIC_BACKEND_URL = os.getenv("PUBLIC_BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Book Reader", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --surface: #111316;
        --panel: #161a1f;
        --panel-2: #1b2027;
        --border: #2a323d;
        --accent: #18a0fb;
        --text: #f2f4f8;
        --muted: #98a2b3;
    }
    .block-container { padding-top: 1.2rem; padding-bottom: 1rem; }
    [data-testid="stSidebar"] { width: 320px; }
    [data-testid="stSidebar"] > div { height: 100vh; overflow-y: auto; padding-top: 0.75rem; }
    [data-testid="stTabs"] { position: relative; z-index: 2; margin-top: 0.6rem; }
    [data-testid="stTabs"] button { font-size: 1.02rem; padding: 0.45rem 1rem; }
    [data-testid="stDialog"] > div { width: 78vw; max-width: 1100px; }
    [data-testid="stDialog"] button[aria-label="Close"],
    [data-testid="stDialog"] button[title="Close"],
    [data-testid="stDialog"] [data-testid="dialogCloseButton"],
    [data-testid="stDialog"] [data-testid="stDialogCloseButton"],
    [data-testid="stDialog"] [data-testid="DialogCloseButton"],
    [data-testid="stDialog"] [aria-label="Close dialog"],
    [data-testid="stDialog"] [data-testid="stDialogHeader"] button,
    [data-testid="stDialog"] header button {
        display: none !important;
        visibility: hidden !important;
    }
    .summary-box {
        border: 1px solid var(--border);
        padding: 14px;
        border-radius: 10px;
        max-height: 420px;
        overflow-y: auto;
        background: var(--panel-2);
        color: var(--text);
    }
    .section-title { font-weight: 600; }
    .summary-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 0.5rem;
    }
    .summary-meta { color: var(--muted); font-size: 0.9rem; }
    .pdf-frame {
        width: 100%;
        height: calc(100vh - 220px);
        border: 1px solid var(--border);
        border-radius: 10px;
        background: #fff;
    }
    .stTextArea textarea {
        background: var(--panel-2);
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: 8px;
    }
    .stButton button {
        border-radius: 8px;
        border: 1px solid var(--border);
    }
    .audio-shell {
        padding: 8px 10px;
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--panel-2);
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .audio-shell button {
        background: var(--panel);
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 6px 10px;
        cursor: pointer;
    }
    @media (max-width: 900px) {
        [data-testid="stSidebar"] { width: 100%; position: relative; }
        [data-testid="stHorizontalBlock"] { flex-direction: column; }
        .pdf-frame { height: calc(100vh - 260px); }
        [data-testid="stDialog"] > div { width: 92vw; }
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


def render_audio_player(audio_bytes: bytes, content_type: str) -> None:
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    html = f"""
    <div class="audio-shell">
      <button onclick="var a=document.getElementById('tts-audio'); a.currentTime=Math.max(0,a.currentTime-10);">-10s</button>
      <button onclick="var a=document.getElementById('tts-audio'); a.currentTime=Math.min(a.duration,a.currentTime+10);">+10s</button>
      <label style="color:#98a2b3;">Speed</label>
      <select onchange="document.getElementById('tts-audio').playbackRate=parseFloat(this.value);" style="background:#161a1f;color:#f2f4f8;border:1px solid #2a323d;border-radius:6px;padding:4px 6px;">
        <option value="0.9">0.9x</option>
        <option value="1" selected>1.0x</option>
        <option value="1.1">1.1x</option>
        <option value="1.25">1.25x</option>
      </select>
      <audio id="tts-audio" controls style="width:100%;">
        <source src="data:{content_type};base64,{b64}">
      </audio>
    </div>
    """
    components_html(html, height=80)


def render_pdf_viewer(book_id: int, page: int) -> None:
    viewer_rev = "v2-qa-1"
    viewer_url = f"{PUBLIC_BACKEND_URL}/books/{book_id}/viewer?page={page}&v={viewer_rev}"
    st.markdown(
        f"<iframe src='{viewer_url}' class='pdf-frame' style='width:100%;min-width:100%;'></iframe>",
        unsafe_allow_html=True,
    )




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
        st.markdown(
            f"<div class='summary-header'><div><strong>Summary</strong><div class='summary-meta'>Pages {section['page_start']} - {section['page_end']}</div></div></div>",
            unsafe_allow_html=True,
        )
        if st.button("Close", key=f"close_summary_{section['id']}"):
            st.session_state["show_summary"] = False
            st.session_state["selected_section"] = None
            st.rerun()
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

        cols = st.columns([1, 1, 1])
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
            render_audio_player(audio_bytes, content_type)

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

        tabs = st.tabs(["Summary", "Figures"])
        with tabs[0]:
            if content:
                st.text_area("Summary", content, height=460, disabled=True)
            else:
                st.info("No summary available yet. Click Regenerate to create one.")
        with tabs[1]:
            assets_response = api_get(
                f"/sections/{section['id']}/assets", params={"recursive": str(recursive).lower()}
            )
            assets = assets_response.json() if assets_response else []
            if assets:
                for asset in assets:
                    image_url = f"{PUBLIC_BACKEND_URL}/assets/{asset['id']}"
                    st.image(image_url, caption=asset.get("caption"))
            else:
                st.caption("No figures for this section.")

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
st.sidebar.checkbox("Recursive summary", value=st.session_state.get("recursive_summary", True), key="recursive_summary")

tabs = st.tabs(["Reader", "Summaries Explorer"])

if selected_label != "None":
    book = book_options[selected_label]
    st_autorefresh(interval=1000, key="summary_autorefresh", debounce=True)
    progress = api_get(f"/books/{book['id']}/progress")
    last_page = progress.json().get("last_page", 1) if progress and progress.status_code == 200 else 1
    if st.session_state.get("current_book_id") != book["id"]:
        st.session_state["current_book_id"] = book["id"]
        st.session_state["page"] = int(last_page)

    click_event = api_get(f"/books/{book['id']}/summary_click")
    if click_event and click_event.status_code == 200:
        click_data = click_event.json()
        event_page = click_data.get("page")
        if event_page:
            page_for_section = int(event_page)
            section_resp = api_get(
                f"/books/{book['id']}/sections/by_page", params={"page": page_for_section}
            )
            if section_resp and section_resp.status_code == 200:
                st.session_state["page"] = page_for_section
                st.session_state["selected_section"] = section_resp.json()
                st.session_state["show_summary"] = True

    with tabs[0]:
        st.subheader("PDF Viewer")
        page = st.session_state.get("page", 1)
        api_put(f"/books/{book['id']}/progress", json={"last_page": int(page), "last_section_id": None})
        render_pdf_viewer(int(book["id"]), int(page))

        recursive = st.session_state.get("recursive_summary", True)

        if st.session_state.get("show_summary") and st.session_state.get("selected_section"):
            st.session_state["summary_context_recursive"] = recursive

    with tabs[1]:
        st.subheader("Summaries Explorer")
        tree_response = api_get(f"/books/{book['id']}/sections")
        tree = tree_response.json() if tree_response else []

        def on_explorer_click(node):
            st.session_state["selected_section"] = node
            st.session_state["show_summary"] = True

        render_tree_explorer(tree, on_explorer_click)

        if st.session_state.get("show_summary") and st.session_state.get("selected_section"):
            st.session_state["summary_context_recursive"] = True

    if st.session_state.get("show_summary") and st.session_state.get("selected_section"):
        summary_dialog(
            st.session_state["selected_section"],
            st.session_state.get("summary_context_recursive", True),
        )
else:
    with tabs[0]:
        st.info("Upload a PDF and select a book to begin.")
    with tabs[1]:
        st.info("Upload a PDF and select a book to begin.")
