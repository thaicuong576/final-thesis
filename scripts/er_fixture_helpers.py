"""Helper functions for ER fixtures generation and locator humanization."""

from __future__ import annotations


def humanize_locator(raw: str) -> str:
    """Humanize a machine-structured source locator string into a readable string.

    Specifications per ER-3 §4:
    - printed_page:N -> 'tr. N'; printed_pages:2_and_3_and_7 -> 'tr. 2, 3, 7'; page:N -> 'tr. N'
    - section/sections -> replace '_' with ' ', keep original letters
    - drop keys: extraction, denominator, groups, row, pdf_page, pdf_pages, formula, equity_scope, columns, ocr_engine, prior_fy_basis
    - join tokens with ' · '
    - fallback to raw if not parseable
    """
    if not raw:
        return ""

    parts = [p.strip() for p in raw.split(";") if p.strip()]
    kv: dict[str, str] = {}
    for part in parts:
        if ":" in part:
            k, v = part.split(":", 1)
            kv[k.strip()] = v.strip()

    tokens: list[str] = []

    # 1. Page
    if "printed_page" in kv:
        tokens.append(f"tr. {kv['printed_page']}")
    elif "printed_pages" in kv:
        p_val = kv["printed_pages"].replace("_and_", ", ").replace(",", ", ")
        p_val = ", ".join(p.strip() for p in p_val.split(","))
        tokens.append(f"tr. {p_val}")
    elif "page" in kv:
        tokens.append(f"tr. {kv['page']}")
    elif "pdf_page" in kv and ("section" not in kv and "sections" not in kv):
        tokens.append(f"tr. {kv['pdf_page']}")
    elif "pdf_pages" in kv and ("section" not in kv and "sections" not in kv):
        val = ", ".join(p.strip() for p in kv["pdf_pages"].split(","))
        tokens.append(f"tr. {val}")

    # 2. Section / statement / table
    sec = kv.get("section") or kv.get("sections")
    if sec:
        sec_clean = sec.replace("_", " ")
        if "|" in sec_clean:
            sec_clean = " · ".join(s.strip() for s in sec_clean.split("|"))
        tokens.append(sec_clean)
    elif "statement" in kv:
        stmt_clean = kv["statement"].replace("_", " ")
        tokens.append(stmt_clean)
    elif "table" in kv:
        tbl_clean = kv["table"].replace("_", " ")
        tokens.append(tbl_clean)

    if tokens:
        return " · ".join(tokens)
    return raw
