import os
import tempfile
import streamlit as st

from parser_pdf import load_pdf, is_suspicious
from recovery import recover_text
from diagnostics import get_diagnostics
from exporter import export_all_txt, export_diagnostics_json, export_recovered_pdf

st.set_page_config(page_title="PDF Parser", layout="wide")

# Hide Streamlit's default UI chrome (hamburger menu, footer, deploy button)
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {display: none;}
    .stDeployButton {display: none;}
    [data-testid="manage-app-button"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("PDF Parser & Recovery Tool")

uploaded = st.file_uploader("Upload a PDF file", type="pdf")

if not uploaded:
    st.info("Upload a PDF to begin analysis.")
    st.stop()


@st.cache_data(show_spinner="Analyzing PDF…")
def analyze(file_bytes: bytes):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(file_bytes)
        path = f.name
    pages = load_pdf(path)
    os.unlink(path)
    recoveries = [recover_text(p.text) for p in pages]
    return pages, recoveries


@st.cache_data(show_spinner="Preparing exports…")
def build_exports(file_bytes: bytes):
    pages, recoveries = analyze(file_bytes)
    txt = export_all_txt(pages, recoveries)
    diag_json = export_diagnostics_json(pages, recoveries)
    pdf_bytes = export_recovered_pdf(file_bytes, pages, recoveries)
    return txt, diag_json, pdf_bytes


file_bytes = uploaded.read()
pages, recoveries = analyze(file_bytes)

suspicious_count = sum(1 for p in pages if is_suspicious(p))
st.caption(f"{len(pages)} pages • {suspicious_count} suspicious")

# --- Sidebar: page list + global exports ---
with st.sidebar:
    st.subheader("Pages")
    labels = [
        f"{'⚠' if is_suspicious(p) else '✓'} Page {p.number}"
        for p in pages
    ]
    selected = st.selectbox("Select page", labels, label_visibility="collapsed")
    idx = labels.index(selected)
    page = pages[idx]
    recovered, strategy, confidence = recoveries[idx]

    st.divider()
    st.markdown("**Export All Pages**")

    txt_data, diag_data, pdf_data = build_exports(file_bytes)

    st.download_button(
        "⬇ Recovered Text (.txt)",
        txt_data,
        "recovered.txt",
        "text/plain",
        use_container_width=True,
    )
    st.download_button(
        "⬇ Diagnostics (.json)",
        diag_data,
        "diagnostics.json",
        "application/json",
        use_container_width=True,
    )
    st.download_button(
        "⬇ Recovered PDF",
        pdf_data,
        "recovered.pdf",
        "application/pdf",
        use_container_width=True,
    )

# --- Main: selected page ---
st.subheader(f"Page {page.number}")

col1, col2, col3 = st.columns(3)
col1.metric("Characters", len(page.text))
col2.metric("Recovery Confidence", f"{confidence:.0%}")
col3.metric("Strategy", strategy)

tab_orig, tab_rec, tab_diag, tab_debug = st.tabs(
    ["Original Text", "Recovered Text", "Diagnostics", "Debug"]
)

with tab_orig:
    # Dynamic key per page so Streamlit doesn't cache the previous page's value
    st.text_area(
        "Raw text from PyMuPDF",
        page.text or "(empty — no embedded text extracted)",
        height=400,
        key=f"orig_{page.number}",
    )

with tab_rec:
    st.text_area(
        "Recovered text",
        recovered or "(empty)",
        height=400,
        key=f"rec_{page.number}",
    )
    if recovered and recovered.strip():
        st.download_button(
            "⬇ Download this page",
            recovered,
            f"page_{page.number}_recovered.txt",
            key=f"dl_{page.number}",
        )

with tab_diag:
    diag = get_diagnostics(page, strategy, confidence)
    st.json(diag)

with tab_debug:
    with st.expander("Hex dump (first 256 bytes of raw text)"):
        raw = page.text.encode("utf-8", errors="replace")
        hex_lines = []
        for i in range(0, min(256, len(raw)), 16):
            chunk = raw[i:i + 16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            asc_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            hex_lines.append(f"{i:04x}  {hex_part:<48}  {asc_part}")
        st.code("\n".join(hex_lines) or "(no data)")

    with st.expander("Span information (first 10 spans)"):
        st.write(page.spans if page.spans else "No span data")

    with st.expander("Font dictionary"):
        st.write(page.fonts if page.fonts else "No fonts detected")

    with st.expander("Unicode code points (first 100 chars)"):
        points = [(repr(c), hex(ord(c))) for c in page.text[:100]]
        st.write(points)
