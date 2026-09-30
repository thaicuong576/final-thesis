"""Helper functions for ER fixtures generation and locator humanization."""

from __future__ import annotations


def humanize_locator(raw: str) -> str:
    """Humanize a machine-structured source locator string into a readable string.

    Specifications per ER-3 §4 and Task FIXM-D:
    - printed_page:N -> 'tr. N'; printed_pages:2_and_3 -> 'tr. 2, 3'; page:N -> 'tr. N'
    - pdf_pages:6,8 -> 'tr. 6, 8'; pdf_page:17 -> 'tr. 17' (when printed page not available)
    - section/sections, statement, table, note -> replace '_' with ' ', keep original case, join '|' with ' · '
    - drop technical keys: formula, equity_scope, extraction, denominator, groups, row, columns, ocr_engine, prior_fy_basis
    - join tokens with ' · '
    - never output raw key=value machine strings
    """
    if not raw:
        return ""

    parts = [p.strip() for p in raw.split(";") if p.strip()]
    kv: dict[str, str] = {}
    for part in parts:
        if ":" in part:
            k, v = part.split(":", 1)
            kv[k.strip()] = v.strip()
        elif "=" in part:
            k, v = part.split("=", 1)
            kv[k.strip()] = v.strip()

    tokens: list[str] = []

    def _format_pages(val: str) -> str:
        cleaned = val.replace("_and_", ", ").replace("|", ", ")
        items = [p.strip() for p in cleaned.split(",") if p.strip()]
        return ", ".join(items)

    # 1. Page
    if "printed_page" in kv:
        tokens.append(f"tr. {_format_pages(kv['printed_page'])}")
    elif "printed_pages" in kv:
        tokens.append(f"tr. {_format_pages(kv['printed_pages'])}")
    elif "page" in kv:
        tokens.append(f"tr. {_format_pages(kv['page'])}")
    elif "pages" in kv:
        tokens.append(f"tr. {_format_pages(kv['pages'])}")
    elif "pdf_page" in kv:
        tokens.append(f"tr. {_format_pages(kv['pdf_page'])}")
    elif "pdf_pages" in kv:
        tokens.append(f"tr. {_format_pages(kv['pdf_pages'])}")

    # 2. Section / Statement / Table / Note
    sec = kv.get("section") or kv.get("sections")
    if sec:
        sec_clean = sec.replace("_", " ")
        if "|" in sec_clean:
            sec_clean = " · ".join(s.strip() for s in sec_clean.split("|"))
        tokens.append(sec_clean)
    elif "statement" in kv or "statements" in kv:
        stmt = kv.get("statement") or kv.get("statements") or ""
        stmt_clean = stmt.replace("_", " ")
        if "|" in stmt_clean:
            stmt_clean = " · ".join(s.strip() for s in stmt_clean.split("|"))
        tokens.append(stmt_clean)
    elif "table" in kv or "tables" in kv:
        tbl = kv.get("table") or kv.get("tables") or ""
        tbl_clean = tbl.replace("_", " ")
        if "|" in tbl_clean:
            tbl_clean = " · ".join(s.strip() for s in tbl_clean.split("|"))
        tokens.append(tbl_clean)
    elif "note" in kv or "notes" in kv:
        note_val = kv.get("note") or kv.get("notes") or ""
        note_clean = note_val.replace("_", " ")
        if "|" in note_clean:
            note_clean = " · ".join(s.strip() for s in note_clean.split("|"))
        tokens.append(note_clean)

    if tokens:
        return " · ".join(tokens)

    # If key-value pairs were present but only technical dropped keys existed, return empty
    if kv:
        return ""
    return raw.strip()
