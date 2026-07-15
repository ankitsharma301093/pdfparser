import fitz
from dataclasses import dataclass, field


@dataclass
class PageData:
    number: int
    text: str
    width: float
    height: float
    rotation: int
    fonts: list = field(default_factory=list)
    blocks: list = field(default_factory=list)
    images: list = field(default_factory=list)
    spans: list = field(default_factory=list)


def load_pdf(path: str) -> list[PageData]:
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        spans = []
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    spans.extend(line.get("spans", []))
        pages.append(PageData(
            number=i + 1,
            text=text,
            width=page.rect.width,
            height=page.rect.height,
            rotation=page.rotation,
            fonts=page.get_fonts(),
            blocks=page.get_text("blocks"),
            images=page.get_images(),
            spans=spans[:20],
        ))
    doc.close()
    return pages


def is_suspicious(page: PageData) -> bool:
    if not page.text:
        return False
    null_count = page.text.count('\x00')
    if null_count > 10:
        return True
    non_print = sum(1 for c in page.text if not c.isprintable() and c not in '\n\t\r')
    return non_print / len(page.text) > 0.1
