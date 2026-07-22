"""Output sanitization for untrusted content (M2 FR-4).

Mitigation mechanisms for threats S8 and S9 (ARCHITECTURE section 7; tracked in
docs/THREAT-MODEL.md): terminal escape / control-character injection via stored
or echoed content, and CSV formula injection in exports. Records are untrusted
input (S10) — the storage layer's read/display/export paths (FR-5/FR-6) apply
these mechanisms to every record field before it reaches a terminal or a file;
this module performs no I/O itself.

- :func:`sanitize_text` removes ANSI CSI sequences wholesale (both the ``ESC [``
  and 8-bit ``0x9B`` forms), then strips C0/C1 control characters and DEL.
  **Preserved:** LF (``\\n``) and TAB (``\\t``) — the only formatting-bearing C0
  characters that cannot initiate an escape sequence; stripping them would
  corrupt every multi-line prompt the storage contract requires to be
  displayable. **Stripped:** everything else, including CR (``\\r``, a
  line-overwrite spoofing vector), ESC (which neutralizes any non-CSI escape
  sequence by removing its introducer), BEL, backspace, DEL, and the full C1
  range (``0x80``-``0x9F``, including the 8-bit CSI introducer).
- :func:`escape_csv_cell` prefix-escapes any cell whose first character is
  ``=``, ``+``, ``-``, ``@``, or TAB with a leading ``'`` — the conventional
  guard that stops spreadsheet applications from interpreting the cell as a
  formula. Already-escaped and benign cells are returned unchanged.

Both functions are deterministic and idempotent.
"""

from __future__ import annotations

import re

# CSI sequences: introducer (ESC "[" or the 8-bit C1 CSI 0x9B), then parameter
# bytes (0x30-0x3F), intermediate bytes (0x20-0x2F), and one final byte (0x40-0x7E).
_CSI_SEQUENCE = re.compile(r"(?:\x1b\[|\x9b)[0-9:;<=>?]*[ -/]*[@-~]")

# C0 controls except LF (0x0A) and TAB (0x09), plus DEL (0x7F) and all C1 (0x80-0x9F).
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")

_CSV_FORMULA_LEADERS = ("=", "+", "-", "@", "\t")


def sanitize_text(text: str) -> str:
    """Return ``text`` safe to print or export: CSI sequences removed wholesale,
    then all C0/C1 controls and DEL stripped (LF and TAB preserved)."""
    without_csi = _CSI_SEQUENCE.sub("", text)
    return _CONTROL_CHARS.sub("", without_csi)


def escape_csv_cell(cell: str) -> str:
    """Return ``cell`` safe for CSV export: a leading ``=``, ``+``, ``-``, ``@``,
    or TAB is prefix-escaped with ``'`` so spreadsheet applications treat the
    cell as text, never as a formula (threat S9)."""
    if cell.startswith(_CSV_FORMULA_LEADERS):
        return "'" + cell
    return cell
