import json
import fitz
from parser_pdf import PageData, is_suspicious
from diagnostics import get_diagnostics


def export_all_txt(pages: list[PageData], recoveries: list) -> str:
    """All pages: original text for clean pages, recovered for corrupted."""
    parts = []
    for i, page in enumerate(pages):
        recovered, _, _ = recoveries[i]
        text = recovered if is_suspicious(page) else page.text
        parts.append(f"=== Page {page.number} ===\n{text.strip() if text else '(empty)'}")
    return "\n\n".join(parts)


def export_diagnostics_json(pages: list[PageData], recoveries: list) -> str:
    diags = []
    for i, page in enumerate(pages):
        _, strategy, confidence = recoveries[i]
        diags.append(get_diagnostics(page, strategy, confidence))
    return json.dumps(diags, indent=2)


def export_recovered_pdf(source_bytes: bytes, pages: list[PageData], recoveries: list) -> bytes:
    """
    Copy clean pages verbatim from the original PDF (preserving style/images).
    Replace corrupted pages with a new text-only page showing recovered content.
    """
    src = fitz.open(stream=source_bytes, filetype="pdf")
    out = fitz.open()

    for i, page in enumerate(pages):
        recovered, _, _ = recoveries[i]
        if is_suspicious(page) and recovered and recovered.strip():
            # Corrupted page — new text page with recovered content
            w = page.width or 612
            h = page.height or 792
            new_p = out.new_page(width=w, height=h)
            margin = 50
            rect = fitz.Rect(margin, margin, w - margin, h - margin)
            # Ensure text is compatible with the Base14 Helvetica font
            clean = recovered.strip().encode("latin-1", errors="replace").decode("latin-1")
            new_p.insert_textbox(
                rect,
                clean,
                fontsize=9,
                fontname="helv",
                color=(0, 0, 0),
            )
        else:
            # Clean page (or unrecoverable) — copy original verbatim
            out.insert_pdf(src, from_page=i, to_page=i)

    src.close()
    buf = out.tobytes(garbage=4, deflate=True)
    out.close()
    return buf
