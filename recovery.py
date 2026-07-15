import re
from collections import Counter


class RecoveryStrategy:
    name: str = "Base"

    def detect(self, text: str) -> float:
        return 0.0

    def recover(self, text: str) -> str:
        return text


class UTF16Caesar(RecoveryStrategy):
    """NULL-byte pages (UTF-16 pattern): strip NULLs then apply Caesar shift."""
    name = "UTF-16 + Caesar Shift"

    def detect(self, text: str) -> float:
        if not text:
            return 0.0
        null_ratio = text.count('\x00') / len(text)
        return min(0.95, null_ratio * 2) if null_ratio > 0.2 else 0.0

    def recover(self, text: str) -> str:
        stripped = text.replace('\x00', '')
        return _apply_shift(stripped, _find_best_shift(stripped)[0]) if stripped else text


class MixedEncoding(RecoveryStrategy):
    """
    Pages mixing byte-range chars (possibly Caesar-shifted) with Unicode glyph
    artifacts (> 127) from fonts that lack a ToUnicode mapping table.
    """
    name = "Mixed: ASCII Extract + Caesar"

    def detect(self, text: str) -> float:
        if not text:
            return 0.0
        unicode_p = sum(1 for c in text if ord(c) > 127 and c.isprintable())
        ratio = unicode_p / len(text)
        return min(0.8, ratio * 1.5) if ratio > 0.05 else 0.0

    def recover(self, text: str) -> str:
        # Decide whether the ASCII chars are already readable or need a shift.
        # Heuristic: if > 25 % of ASCII alpha chars are vowels, the text is already
        # natural language (like page 25). If < 25 %, it's Caesar-shifted (page 43).
        ascii_alpha = [c for c in text if c.isalpha() and ord(c) < 128]
        shift = 0
        if ascii_alpha:
            vowels = sum(1 for c in ascii_alpha if c.lower() in 'aeiou')
            vowel_ratio = vowels / len(ascii_alpha)
            if vowel_ratio < 0.25:
                # Likely Caesar-shifted — find shift using byte-range chars only
                byte_chars = ''.join(c for c in text if 0 < ord(c) < 128 and c not in '\n\t\r')
                shift, _ = _find_best_shift(byte_chars)

        result = []
        for c in text:
            if c in '\n\r':
                result.append(c)
            elif ord(c) > 127:              # Unicode glyph artifact → discard
                result.append(' ')
            elif shift and 0 < ord(c) < 128 and c not in '\t':
                shifted = chr((ord(c) + shift) % 256)
                result.append(shifted if shifted.isprintable() else ' ')
            elif c.isprintable():
                result.append(c)
            else:
                result.append(' ')

        lines = ''.join(result).split('\n')
        return '\n'.join(re.sub(r' {2,}', ' ', line).strip() for line in lines)


class CaesarShift(RecoveryStrategy):
    """Byte-range pages with high non-printable ratio: find and apply best shift."""
    name = "Caesar Shift"

    def detect(self, text: str) -> float:
        if not text:
            return 0.0
        if text.count('\x00') / len(text) > 0.2:
            return 0.0
        unicode_p = sum(1 for c in text if ord(c) > 127 and c.isprintable())
        if unicode_p / len(text) > 0.05:
            return 0.0  # MixedEncoding handles it
        non_print = sum(1 for c in text if not c.isprintable() and c not in '\n\t\r')
        if non_print / len(text) < 0.1:
            return 0.0
        _, score = _find_best_shift(text)
        return score if score > 0.6 else 0.0

    def recover(self, text: str) -> str:
        shift, _ = _find_best_shift(text)
        return _apply_shift(text, shift)


class PrintableCleanup(RecoveryStrategy):
    """Fallback: strip non-printable characters."""
    name = "Printable Cleanup"

    def detect(self, text: str) -> float:
        non_print = sum(1 for c in text if not c.isprintable() and c not in '\n\t\r')
        return (non_print / len(text)) * 0.4 if text else 0.0

    def recover(self, text: str) -> str:
        return ''.join(c if c.isprintable() or c in '\n\t\r' else ' ' for c in text)


def _score_shift(working: list[int], shift: int) -> float:
    total = 0
    for v in working:
        s = (v + shift) % 256
        if 32 <= s <= 126:           # standard ASCII — full credit
            total += 2
        elif chr(s).isprintable():   # extended Latin — half credit
            total += 1
    return total / (len(working) * 2) if working else 0.0


def _find_best_shift(text: str) -> tuple[int, float]:
    """
    Primary heuristic: map the most common char to space (reliable for natural language).
    If primary score > 88 %, trust it immediately (avoids over-fitting to noisy chars
    like the few value-1/2 bytes on page 18 that push a competing shift higher).
    Otherwise fall back to exhaustive 1-127 search.
    """
    working = [ord(c) for c in text if c not in '\n\t\r' and ord(c) < 256]
    if not working:
        return 0, 0.0

    most_common_val = Counter(working).most_common(1)[0][0]
    primary_shift = (32 - most_common_val) % 256
    primary_score = _score_shift(working, primary_shift)

    # High-confidence primary → use immediately
    if primary_score >= 0.88:
        return primary_shift, primary_score

    # Exhaustive search — override only if clearly better (> 7 % margin)
    best_shift, best_score = primary_shift, primary_score
    for shift in range(1, 128):
        s = _score_shift(working, shift)
        if s > best_score + 0.07:
            best_score, best_shift = s, shift

    return best_shift, best_score


def _apply_shift(text: str, shift: int) -> str:
    result = []
    for c in text:
        if c in '\n\t\r':
            result.append(c)
        else:
            shifted = chr((ord(c) + shift) % 256)
            result.append(shifted if shifted.isprintable() else ' ')
    return ''.join(result)


STRATEGIES = [UTF16Caesar(), MixedEncoding(), CaesarShift(), PrintableCleanup()]


def recover_text(text: str) -> tuple[str, str, float]:
    """Returns (recovered_text, strategy_name, confidence 0-1)."""
    if not text:
        return text, "None", 1.0

    non_print = sum(1 for c in text if not c.isprintable() and c not in '\n\t\r')
    if non_print / len(text) < 0.05:
        conf = sum(1 for c in text if c.isprintable()) / len(text)
        return text, "None (already clean)", conf

    best = max(STRATEGIES, key=lambda s: s.detect(text))
    if best.detect(text) < 0.1:
        return text, "None", sum(1 for c in text if c.isprintable()) / len(text)

    recovered = best.recover(text)
    printable = sum(1 for c in recovered if c.isprintable())
    confidence = printable / len(recovered) if recovered else 0.0
    return recovered, best.name, confidence
