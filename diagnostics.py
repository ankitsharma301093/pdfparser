from parser_pdf import PageData


def get_diagnostics(page: PageData, strategy: str = "", confidence: float = 0.0) -> dict:
    text = page.text
    null_count = text.count('\x00')
    printable = sum(1 for c in text if c.isprintable())
    non_printable = len(text) - printable

    if null_count > 10:
        suspected = "UTF-16 encoding + font mapping"
    elif text and non_printable / len(text) > 0.1:
        suspected = "font mapping / Caesar shift"
    elif not text and page.images:
        suspected = "scanned page (no embedded text)"
    elif not text:
        suspected = "empty page"
    else:
        suspected = "none"

    return {
        "page": page.number,
        "dimensions": {"width": round(page.width, 1), "height": round(page.height, 1)},
        "rotation": page.rotation,
        "text_stats": {
            "character_count": len(text),
            "printable": printable,
            "non_printable": non_printable,
            "null_bytes": null_count,
            "utf16_markers": null_count,
        },
        "fonts": [
            {
                "name": f[3],
                "subset": "+" in str(f[3])[:7],
                "type": f[2],
                "encoding": f[5] if len(f) > 5 else "unknown",
            }
            for f in page.fonts
        ],
        "text_blocks": {"count": len(page.blocks)},
        "images": {"count": len(page.images)},
        "heuristics": {
            "looks_like_scanned_page": not text and bool(page.images),
            "looks_like_embedded_text": bool(text),
            "looks_like_encoding_issue": bool(text) and null_count > 10,
            "looks_like_font_mapping_issue": bool(text) and non_printable / len(text) > 0.1 if text else False,
        },
        "recovery": {
            "strategy": strategy,
            "confidence": round(confidence, 3),
            "suspected_issue": suspected,
        },
    }
