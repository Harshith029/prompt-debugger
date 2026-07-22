"""Unit tests for the sanitization module (M2 FR-4).

S8: CSI sequences (both introducer forms) removed wholesale; C0/C1 controls and
DEL stripped; LF/TAB preserved. S9: CSV formula leaders prefix-escaped. Both
functions deterministic and idempotent; benign content byte-identical.
"""

from __future__ import annotations

from prompt_debugger import sanitize

# --- sanitize_text: ANSI CSI removal (S8) ----------------------------------------------


def test_csi_color_and_cursor_sequences_removed_wholesale() -> None:
    assert sanitize.sanitize_text("\x1b[31mred\x1b[0m text") == "red text"
    assert sanitize.sanitize_text("a\x1b[2Jb\x1b[10;10Hc") == "abc"
    # parameter + intermediate bytes before the final byte
    assert sanitize.sanitize_text("x\x1b[?25ly") == "xy"


def test_eight_bit_csi_introducer_removed() -> None:
    assert sanitize.sanitize_text("a\x9b31mb") == "ab"


def test_non_csi_escape_sequences_are_neutralized() -> None:
    # OSC and single-char ESC sequences lose their introducer (ESC is C0); the
    # residue is inert printable text and the terminal threat is removed.
    out = sanitize.sanitize_text("\x1b]0;evil title\x07rest")
    assert "\x1b" not in out and "\x07" not in out
    assert out.endswith("rest")


# --- sanitize_text: control characters (S8) --------------------------------------------


def test_c0_controls_and_del_stripped() -> None:
    assert sanitize.sanitize_text("a\x00b\x07c\x08d\x0be\x0cf\x7fg") == "abcdefg"


def test_carriage_return_stripped_lf_and_tab_preserved() -> None:
    assert sanitize.sanitize_text("line1\r\nline2\tend\r") == "line1\nline2\tend"


def test_c1_range_stripped() -> None:
    assert sanitize.sanitize_text("a\x80b\x9fc\x85d") == "abcd"


def test_printable_unicode_preserved() -> None:
    # NBSP (U+00A0) is the first code point above the C1 range and must survive.
    text = "caf\u00e9 \u2192 \u201cbox\u201d \u00a0 \u2713\nnext\tcol"
    assert sanitize.sanitize_text(text) == text


def test_sanitize_is_deterministic_and_idempotent() -> None:
    dirty = "\x1b[31m a\x00b \x9b1m \r\n"
    once = sanitize.sanitize_text(dirty)
    assert once == sanitize.sanitize_text(dirty)
    assert sanitize.sanitize_text(once) == once


def test_clean_text_is_byte_identical() -> None:
    clean = "Explain how our caching layer works.\n  indented\ttabbed"
    assert sanitize.sanitize_text(clean) == clean


# --- escape_csv_cell (S9) --------------------------------------------------------------


def test_formula_leaders_are_prefix_escaped() -> None:
    assert sanitize.escape_csv_cell("=SUM(A1:A9)") == "'=SUM(A1:A9)"
    assert sanitize.escape_csv_cell("+1234") == "'+1234"
    assert sanitize.escape_csv_cell("-2+3+cmd|' /C calc'!A0") == "'-2+3+cmd|' /C calc'!A0"
    assert sanitize.escape_csv_cell("@thing") == "'@thing"
    assert sanitize.escape_csv_cell("\tleading tab") == "'\tleading tab"


def test_benign_cells_unchanged() -> None:
    for cell in ("hello", "a=b not leading", "", "3.14", "R2 severity", "s1", "'already"):
        assert sanitize.escape_csv_cell(cell) == cell


def test_escape_is_idempotent() -> None:
    once = sanitize.escape_csv_cell("=SUM(A1)")
    assert sanitize.escape_csv_cell(once) == once
