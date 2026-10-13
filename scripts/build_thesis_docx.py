#!/usr/bin/env python3
"""
Build thesis Word document from Markdown sources.

Usage:
    python scripts/build_thesis_docx.py \\
        --template "path/to/template.docx" \\
        --out docs/thesis-v2/build/Khoa-luan.docx

The script:
  1. Opens the template docx (keeps styles, sectPr, footer; clears body content).
  2. Inserts front-matter, TOC fields, chapter content from Markdown files.
  3. Converts Markdown formatting to proper Word styles.
  4. Renders Mermaid (.mmd) diagrams to PNG via mmdc or matplotlib fallback.
"""
from __future__ import annotations

import argparse
import copy
import io
import os
import re
import shutil
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Optional matplotlib import for Mermaid fallback rendering
# ---------------------------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
# (Emu and Pt are already imported from docx.shared above)

# ---------------------------------------------------------------------------
# Paths relative to repo root
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
FIGURES_DIR = REPO_ROOT / "docs" / "thesis-v2" / "figures"

# ---------------------------------------------------------------------------
# Mermaid diagrams (rendered by scripts/thesis_diagrams.py)
# ---------------------------------------------------------------------------
def ensure_mermaid_pngs(figures_dir: Path) -> dict[str, Path]:
    """Render every .mmd in figures_dir to PNG with scripts/thesis_diagrams.py (offline)."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from thesis_diagrams import render

    pngs: dict[str, Path] = {}
    for mmd_file in sorted(figures_dir.glob("*.mmd")):
        png_path = figures_dir / (mmd_file.stem + ".png")
        # Prefer the PNG produced by scripts/render_thesis_mermaid.py (real Mermaid, monochrome);
        # the matplotlib fallback only runs when no PNG exists.
        if not png_path.exists():
            render(mmd_file, png_path)
        pngs[mmd_file.stem] = png_path
    return pngs


def _set_paragraph_style(para, style_name: str, doc: Document) -> None:
    """Safely set paragraph style, falling back to Normal if not found."""
    try:
        para.style = doc.styles[style_name]
    except KeyError:
        try:
            para.style = doc.styles["Normal"]
        except KeyError:
            pass


def _safe_add_paragraph(doc: Document, style_name: str) -> object:
    """Add a paragraph with the given style, falling back to Normal if not found."""
    try:
        return doc.add_paragraph(style=style_name)
    except KeyError:
        para = doc.add_paragraph()
        try:
            para.style = doc.styles["Normal"]
        except KeyError:
            pass
        return para


def _add_page_break_before(para) -> None:
    """Set pageBreakBefore on a paragraph's pPr."""
    pPr = para._p.get_or_add_pPr()
    pb = OxmlElement("w:pageBreakBefore")
    pb.set(qn("w:val"), "1")
    pPr.append(pb)


def _set_run_font(run, size_pt: Optional[float] = None, bold: Optional[bool] = None,
                  italic: Optional[bool] = None, font_name: str = "Times New Roman") -> None:
    """Apply font attributes to a run."""
    run.font.name = font_name
    rPr = run._r.get_or_add_rPr()
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:cs"), font_name)
    # Remove existing rFonts to avoid duplicates
    for existing in rPr.findall(qn("w:rFonts")):
        rPr.remove(existing)
    rPr.insert(0, rFonts)
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic


def _add_toc_field(doc: Document, heading_text: str, field_instr: str) -> None:
    """Add a heading paragraph followed by a TOC/TOF/TOT field instruction."""
    heading = doc.add_paragraph(heading_text, style="Heading 1")
    _add_page_break_before(heading)
    for run in heading.runs:
        _set_run_font(run, size_pt=13, bold=True)

    # Add the field paragraph
    p = doc.add_paragraph()
    _set_paragraph_style(p, "Normal", doc)
    fldChar_begin = OxmlElement("w:fldChar")
    fldChar_begin.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = field_instr
    fldChar_end = OxmlElement("w:fldChar")
    fldChar_end.set(qn("w:fldCharType"), "end")

    r1 = OxmlElement("w:r")
    r1.append(fldChar_begin)
    r2 = OxmlElement("w:r")
    r2.append(instrText)
    r3 = OxmlElement("w:r")
    r3.append(fldChar_end)
    p._p.extend([r1, r2, r3])


# ---------------------------------------------------------------------------
# HTML tag stripping
# ---------------------------------------------------------------------------
_HTML_TAG_RE = re.compile(r'<[^>]+>', re.DOTALL)
_HTML_BR_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)
_HTML_BOLD_OPEN = re.compile(r'<b\s*>', re.IGNORECASE)
_HTML_BOLD_CLOSE = re.compile(r'</b>', re.IGNORECASE)
_HTML_EM_OPEN = re.compile(r'<(?:em|i)\s*>', re.IGNORECASE)
_HTML_EM_CLOSE = re.compile(r'</(?:em|i)>', re.IGNORECASE)


def _clean_html(text: str) -> str:
    """Convert simple HTML tags to plain/markdown equivalents."""
    text = _HTML_BR_RE.sub('\n', text)
    text = _HTML_BOLD_OPEN.sub('**', text)
    text = _HTML_BOLD_CLOSE.sub('**', text)
    text = _HTML_EM_OPEN.sub('*', text)
    text = _HTML_EM_CLOSE.sub('*', text)
    text = _HTML_TAG_RE.sub('', text)
    return text


# ---------------------------------------------------------------------------
# Inline Markdown → runs
# ---------------------------------------------------------------------------
# Pattern pieces: **bold**, *italic*, `code`, plain
_INLINE_RE = re.compile(
    r'(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`(.+?)`)',
    re.DOTALL,
)


def _add_inline_runs(para, text: str, base_size: float = 13,
                     base_font: str = "Times New Roman") -> None:
    """Parse inline markdown and add runs to para."""
    last = 0
    for m in _INLINE_RE.finditer(text):
        # Plain text before match
        if m.start() > last:
            run = para.add_run(text[last:m.start()])
            _set_run_font(run, size_pt=base_size, font_name=base_font)
        if m.group(1):  # **bold**
            run = para.add_run(m.group(2))
            _set_run_font(run, size_pt=base_size, bold=True, font_name=base_font)
        elif m.group(3):  # *italic*
            run = para.add_run(m.group(4))
            _set_run_font(run, size_pt=base_size, italic=True, font_name=base_font)
        elif m.group(5):  # `code`
            run = para.add_run(m.group(6))
            _set_run_font(run, size_pt=11, font_name="Consolas")
        last = m.end()
    # Remaining
    if last < len(text):
        run = para.add_run(text[last:])
        _set_run_font(run, size_pt=base_size, font_name=base_font)


# ---------------------------------------------------------------------------
# Normal paragraph first-line indent
# ---------------------------------------------------------------------------
def _set_normal_indent(para) -> None:
    """Set first-line indent 1.27 cm for Normal paragraphs."""
    pPr = para._p.get_or_add_pPr()
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:firstLine"), "720")  # 720 twips = 1.27 cm


def _clear_indent(para) -> None:
    """Remove first-line indent."""
    pPr = para._p.get_or_add_pPr()
    ind = pPr.find(qn("w:ind"))
    if ind is not None:
        pPr.remove(ind)


def _set_para_alignment(para, alignment) -> None:
    para.alignment = alignment


# ---------------------------------------------------------------------------
# Markdown Table parser
# ---------------------------------------------------------------------------
def _parse_md_table(lines: list[str]) -> Optional[list[list[str]]]:
    """Parse markdown table lines to list of rows (each row is list of cells)."""
    rows = []
    for line in lines:
        line = line.strip()
        if re.match(r'^\|?[-:| ]+\|?$', line):
            continue  # separator row
        if line.startswith('|') or '|' in line:
            cells = [c.strip() for c in line.strip('|').split('|')]
            rows.append(cells)
    return rows if rows else None


def _apply_table_borders(table) -> None:
    """Apply full borders to all cells via XML (for templates lacking Table Grid)."""
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border_el = OxmlElement(f"w:{side}")
        border_el.set(qn("w:val"), "single")
        border_el.set(qn("w:sz"), "4")
        border_el.set(qn("w:space"), "0")
        border_el.set(qn("w:color"), "000000")
        tblBorders.append(border_el)
    # Remove existing tblBorders
    for existing in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(existing)
    tblPr.append(tblBorders)


def _add_md_table(doc: Document, table_lines: list[str]) -> None:
    """Add a markdown table as a Word table."""
    rows = _parse_md_table(table_lines)
    if not rows:
        return
    n_cols = max(len(r) for r in rows)
    # Pad short rows
    rows = [r + [''] * (n_cols - len(r)) for r in rows]

    table = doc.add_table(rows=len(rows), cols=n_cols)
    # Try to apply Table Grid style; fall back gracefully
    for style_name in ("Table Grid", "Normal Table", "TableNormal", "Table Normal"):
        try:
            table.style = style_name
            break
        except KeyError:
            continue
    _apply_table_borders(table)

    _format_table(table, rows)


def _set_all_fonts(run, name: str = "Times New Roman", size_pt: float = 12) -> None:
    """Force a font on every script slot so Word never falls back to the style font."""
    run.font.name = name
    run.font.size = Pt(size_pt)
    rpr = run._r.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)


def _format_table(table, rows: list[list[str]]) -> None:
    """Academic table layout: TNR 12, single spacing, bold shaded header repeated on each page."""
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.shared import Pt as _Pt

    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = table._tbl.tblPr
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:type"), "pct")
    tblW.set(qn("w:w"), "5000")  # 100% of the text width
    cell_mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", "40"), ("bottom", "40"), ("left", "80"), ("right", "80")):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), val)
        el.set(qn("w:type"), "dxa")
        cell_mar.append(el)
    for existing in tblPr.findall(qn("w:tblCellMar")):
        tblPr.remove(existing)
    tblPr.append(cell_mar)

    for row_i, row_cells in enumerate(rows):
        tr = table.rows[row_i]
        is_header = row_i == 0
        if is_header:
            trPr = tr._tr.get_or_add_trPr()
            hdr = OxmlElement("w:tblHeader")
            hdr.set(qn("w:val"), "true")
            trPr.append(hdr)
        for col_i, cell_text in enumerate(row_cells):
            cell = tr.cells[col_i]
            para = cell.paragraphs[0]
            _add_inline_runs(para, _clean_html(cell_text), base_size=12)
            pf = para.paragraph_format
            pf.first_line_indent = _Pt(0)
            pf.left_indent = _Pt(0)
            pf.space_before = _Pt(2)
            pf.space_after = _Pt(2)
            pf.line_spacing = 1.0
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER if is_header else WD_ALIGN_PARAGRAPH.LEFT
            for run in para.runs:
                # Tables are Times New Roman throughout, including inline code spans.
                _set_all_fonts(run, "Times New Roman", 12)
                if is_header:
                    run.font.bold = True
            if is_header:
                tcPr = cell._tc.get_or_add_tcPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "E7E6E6")
                tcPr.append(shd)


# ---------------------------------------------------------------------------
# Image insertion
# ---------------------------------------------------------------------------
def _add_image(doc: Document, img_path: Path) -> None:
    """Add an image centered at max 15 cm width."""
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _clear_indent(para)
    try:
        run = para.add_run()
        width_cm = 15.0
        try:  # keep tall screenshots within the page: fit a 15 x 20 cm box
            from PIL import Image as _Image

            with _Image.open(img_path) as _im:
                w_px, h_px = _im.size
            width_cm = min(15.0, 20.0 * w_px / h_px)
        except Exception:  # noqa: BLE001 - PIL is optional; fall back to full width
            pass
        run.add_picture(str(img_path), width=Cm(width_cm))
    except Exception as e:
        print(f"  [image] WARNING: Could not insert image {img_path}: {e}")
        run = para.add_run(f"[Image: {img_path.name}]")


# ---------------------------------------------------------------------------
# Caption paragraph
# ---------------------------------------------------------------------------
CAPTION_FIGURE_STYLE = "Caption Figure"
CAPTION_TABLE_STYLE = "Caption Table"


def _ensure_caption_style(doc: Document, name: str):
    """Create a caption paragraph style (based on Normal) so TOC \t can list it."""
    from docx.enum.style import WD_STYLE_TYPE
    try:
        return doc.styles[name]
    except KeyError:
        st = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = doc.styles["Normal"]
        st.font.italic = True
        st.font.size = Pt(12)
        st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        st.paragraph_format.first_line_indent = Pt(0)
        st.quick_style = True
        return st


def _add_caption(doc: Document, text: str) -> None:
    """Add a caption paragraph with a figure/table caption style (centered, italic, no indent)."""
    name = CAPTION_TABLE_STYLE if text.startswith("Bảng") else CAPTION_FIGURE_STYLE
    para = doc.add_paragraph(style=_ensure_caption_style(doc, name))
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _clear_indent(para)
    run = para.add_run(text)
    _set_run_font(run, size_pt=12, italic=True, font_name="Times New Roman")


# ---------------------------------------------------------------------------
# Markdown → Document conversion
# ---------------------------------------------------------------------------
_FIGURE_REF_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)', re.UNICODE)
_CAPTION_HINH_RE = re.compile(r'^Hình\s+\d[\d.]*\s*:', re.UNICODE)
_CAPTION_BANG_RE = re.compile(r'^Bảng\s+\d[\d.]*\s*:', re.UNICODE)


_EMPHASIS_WRAP_RE = re.compile(r'^(\*\*|\*|__|_)(.+?)\1$')
_FIGURE_NUMBER_RE = re.compile(r'^Hình\s+(\d+)\.(\d+)', re.UNICODE)
_MD_LINK_RE = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')


def _strip_emphasis_wrap(text: str) -> str:
    """'*Hình 3.1: ...*' -> 'Hình 3.1: ...' (whole-line emphasis only)."""
    m = _EMPHASIS_WRAP_RE.match(text.strip())
    return m.group(2).strip() if m else text.strip()


def _is_caption_line(text: str) -> bool:
    plain = _strip_emphasis_wrap(text)
    return bool(_CAPTION_HINH_RE.match(plain) or _CAPTION_BANG_RE.match(plain))


def _figure_png_for_caption(caption: str, pngs: dict[str, Path]) -> Optional[Path]:
    """Map 'Hình 3.1: ...' to figures/hinh-3-1-*.png."""
    m = _FIGURE_NUMBER_RE.match(caption)
    if not m:
        return None
    prefix = f"hinh-{m.group(1)}-{m.group(2)}-"
    for stem, path in sorted(pngs.items()):
        if stem.startswith(prefix) or stem == prefix.rstrip("-"):
            return path
    return None


def _flatten_md_links(md_text: str) -> str:
    """[text](http://x) -> 'text (http://x)'; relative links -> 'text'."""
    def repl(m: re.Match) -> str:
        text, url = m.group(1), m.group(2).strip()
        return f"{text} ({url})" if url.startswith(("http://", "https://")) else text
    return _MD_LINK_RE.sub(repl, md_text)


def _shift_heading_levels(md_text: str, shift: int, drop_title: bool) -> str:
    """Promote headings by `shift` levels; optionally drop the first level-1 title line."""
    out: list[str] = []
    dropped = not drop_title
    for line in md_text.splitlines():
        m = re.match(r'^(#{1,6}) (.*)$', line)
        if m:
            level = len(m.group(1))
            if not dropped and level == 1:
                dropped = True
                continue
            level = max(1, level - shift)
            out.append("#" * level + " " + m.group(2))
        else:
            out.append(line)
    return "\n".join(out)


def _find_image_for_ref(ref_text: str, figures_dir: Path, pngs: dict[str, Path]) -> Optional[Path]:
    """Try to find an image file by reference text (path or stem matching)."""
    # Direct path reference
    img_path = Path(ref_text)
    if img_path.exists():
        return img_path
    # Relative to figures_dir
    candidate = figures_dir / ref_text
    if candidate.exists():
        return candidate
    # Stem matching in pngs dict
    stem = Path(ref_text).stem
    if stem in pngs:
        return pngs[stem]
    # Partial stem match
    for k, v in pngs.items():
        if stem.lower() in k.lower() or k.lower() in stem.lower():
            return v
    return None


def convert_markdown_to_doc(
    doc: Document,
    md_text: str,
    is_first_chapter: bool = False,
    figures_dir: Optional[Path] = None,
    pngs: Optional[dict[str, Path]] = None,
) -> None:
    """Parse Markdown text and append content to doc."""
    if figures_dir is None:
        figures_dir = FIGURES_DIR
    if pngs is None:
        pngs = {}

    md_text = _flatten_md_links(_clean_html(md_text))
    lines = md_text.splitlines()
    i = 0
    first_h1 = True  # Track if this is the first heading 1 to decide page break
    last_was_image = False

    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()

        # --- Fenced code block ---
        # ```mermaid blocks are the source of figures already rendered to PNG and
        # inserted at their "Hình X.Y" caption, so they are skipped. Other fences are
        # kept as monospace paragraphs.
        fence = re.match(r'^\s*(```|~~~)\s*([\w-]*)', stripped)
        if fence:
            marker, lang = fence.group(1), fence.group(2).lower()
            i += 1
            block: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith(marker):
                block.append(lines[i].rstrip())
                i += 1
            i += 1  # closing fence
            if lang == "mermaid":
                continue
            for code_line in block:
                para = doc.add_paragraph()
                _set_paragraph_style(para, "Normal", doc)
                _clear_indent(para)
                run = para.add_run(code_line.strip() or " ")
                _set_run_font(run, size_pt=10, font_name="Consolas")
            continue

        # --- Heading 1 ---
        if stripped.startswith('# ') and not stripped.startswith('## '):
            title = stripped[2:].strip()
            para = _safe_add_paragraph(doc, "Heading 1")
            run = para.add_run(title.upper())
            _set_run_font(run, size_pt=13, bold=True)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if not (is_first_chapter and first_h1):
                _add_page_break_before(para)
            first_h1 = False
            i += 1
            continue

        # --- Heading 2 ---
        if stripped.startswith('## ') and not stripped.startswith('### '):
            title = stripped[3:].strip()
            para = _safe_add_paragraph(doc, "Heading 2")
            run = para.add_run(title)
            _set_run_font(run, size_pt=13, bold=True)
            i += 1
            continue

        # --- Heading 3 ---
        if stripped.startswith('### ') and not stripped.startswith('#### '):
            title = stripped[4:].strip()
            para = _safe_add_paragraph(doc, "Heading 3")
            run = para.add_run(title)
            _set_run_font(run, size_pt=13, bold=True)
            i += 1
            continue

        # --- Heading 4 ---
        if stripped.startswith('#### '):
            title = stripped[5:].strip()
            para = _safe_add_paragraph(doc, "Heading 4")
            run = para.add_run(title)
            _set_run_font(run, size_pt=13, bold=True)
            i += 1
            continue

        # --- Image ---
        img_match = _FIGURE_REF_RE.match(stripped)
        if img_match:
            alt_text = img_match.group(1)
            ref_text = img_match.group(2)
            img_path = _find_image_for_ref(ref_text, figures_dir, pngs)
            if img_path and img_path.exists():
                _add_image(doc, img_path)
                last_was_image = True
            else:
                print(f"  [image] WARNING: Image not found: {ref_text}")
                para = doc.add_paragraph(f"[Hình: {alt_text or ref_text}]")
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _clear_indent(para)
            i += 1
            continue

        # --- Caption line (Hình X.Y: ... or Bảng X.Y: ..., optionally wrapped in *...*) ---
        if _is_caption_line(stripped):
            caption = _strip_emphasis_wrap(stripped)
            if caption.startswith("Hình") and not last_was_image:
                png = _figure_png_for_caption(caption, pngs)
                if png is not None:
                    _add_image(doc, png)
                else:
                    print(f"  [image] WARNING: no diagram PNG for caption: {caption[:40]}")
            _add_caption(doc, caption)
            last_was_image = False
            i += 1
            continue
        if stripped:
            last_was_image = False

        # --- Blockquote ---
        if stripped.startswith('> '):
            para = _safe_add_paragraph(doc, "Normal")
            _add_inline_runs(para, stripped[2:].strip(), base_size=13)
            # Set left indent
            pPr = para._p.get_or_add_pPr()
            ind = OxmlElement("w:ind")
            ind.set(qn("w:left"), "720")
            pPr.append(ind)
            i += 1
            continue

        # --- Markdown table ---
        if stripped.startswith('|') or (i + 1 < len(lines) and re.match(r'^\|?[-:| ]+\|?$', lines[i + 1].strip()) and '|' in stripped):
            # Collect table lines
            table_lines = []
            while i < len(lines) and (lines[i].strip().startswith('|') or re.match(r'^\|?[-:| ]+\|?$', lines[i].strip())):
                table_lines.append(lines[i])
                i += 1
            _add_md_table(doc, table_lines)
            continue

        # --- Unordered list item ---
        if re.match(r'^[\-\*\+] ', stripped):
            text = stripped[2:].strip()
            para = _safe_add_paragraph(doc, "List Bullet")
            _add_inline_runs(para, text, base_size=13)
            _clear_indent(para)
            # Add bullet manually if List Bullet style not present
            if para.style and para.style.name not in ("List Bullet", "List Paragraph"):
                run = para.runs[0] if para.runs else para.add_run()
                # prepend bullet character
                existing_text = "".join(r.text for r in para.runs)
                for r in para.runs:
                    r.text = ""
                para.add_run("• " + existing_text)
            i += 1
            continue

        # --- Ordered list item ---
        if re.match(r'^\d+\. ', stripped):
            num_m = re.match(r'^(\d+)\. ', stripped)
            num_prefix = num_m.group(0) if num_m else ""
            text = re.sub(r'^\d+\. ', '', stripped).strip()
            para = _safe_add_paragraph(doc, "List Number")
            _add_inline_runs(para, text, base_size=13)
            _clear_indent(para)
            # Prepend number manually if style not applied
            if para.style and para.style.name not in ("List Number", "List Paragraph"):
                existing_text = "".join(r.text for r in para.runs)
                for r in para.runs:
                    r.text = ""
                para.add_run(num_prefix + existing_text)
            i += 1
            continue

        # --- Horizontal rule (skip) ---
        if re.match(r'^[-*_]{3,}$', stripped):
            i += 1
            continue

        # --- Empty line ---
        if not stripped:
            i += 1
            continue

        # --- Normal paragraph ---
        # Collect continuation lines (no blank line, not a heading/list/etc.)
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].rstrip()
            if (not nxt or
                    nxt.startswith('#') or
                    re.match(r'^[\-\*\+] ', nxt) or
                    re.match(r'^\d+\. ', nxt) or
                    nxt.startswith('|') or
                    nxt.startswith('> ') or
                    re.match(r'^[-*_]{3,}$', nxt) or
                    _FIGURE_REF_RE.match(nxt) or
                    _is_caption_line(nxt)):
                break
            para_lines.append(nxt)
            i += 1
        full_text = ' '.join(para_lines)
        para = doc.add_paragraph(style="Normal")
        _add_inline_runs(para, full_text, base_size=13)
        _set_normal_indent(para)
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # end while


# ---------------------------------------------------------------------------
# Template preparation
# ---------------------------------------------------------------------------
def prepare_template(template_path: str) -> Document:
    """Open template docx, clear body content, keep styles and sectPr."""
    doc = Document(template_path)
    body = doc.element.body

    # Collect sectPr (last element, typically)
    sectPr = body.find(qn("w:sectPr"))

    # Remove all child elements except sectPr
    to_remove = [el for el in body if el.tag != qn("w:sectPr")]
    for el in to_remove:
        body.remove(el)

    # Ensure sectPr is at end
    if sectPr is not None and sectPr not in list(body):
        body.append(sectPr)

    return doc


# ---------------------------------------------------------------------------
# Front matter title page
# ---------------------------------------------------------------------------
def add_front_matter(doc: Document, md_text: str) -> None:
    """Add front matter page (title page) from Markdown."""
    lines = md_text.splitlines()
    # Use a centered approach for the title page
    for line in lines:
        stripped = line.rstrip()
        if not stripped or stripped.startswith('---'):
            # Add spacing paragraph
            para = doc.add_paragraph()
            _set_paragraph_style(para, "Normal", doc)
            _clear_indent(para)
            continue
        if stripped.startswith('# ') and not stripped.startswith('## '):
            text = stripped[2:].strip()
            para = doc.add_paragraph()
            _set_paragraph_style(para, "Normal", doc)
            run = para.add_run(text.upper())
            _set_run_font(run, size_pt=16, bold=True)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _clear_indent(para)
        elif stripped.startswith('## '):
            text = stripped[3:].strip()
            para = doc.add_paragraph()
            _set_paragraph_style(para, "Normal", doc)
            run = para.add_run(text)
            _set_run_font(run, size_pt=14, bold=True)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _clear_indent(para)
        elif stripped.startswith('**') and stripped.endswith('**'):
            text = stripped.strip('*')
            para = doc.add_paragraph()
            _set_paragraph_style(para, "Normal", doc)
            run = para.add_run(text)
            _set_run_font(run, size_pt=13, bold=True)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _clear_indent(para)
        else:
            para = doc.add_paragraph()
            _set_paragraph_style(para, "Normal", doc)
            _add_inline_runs(para, stripped, base_size=13)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _clear_indent(para)


# ---------------------------------------------------------------------------
# References extraction
# ---------------------------------------------------------------------------
def extract_references(md_text: str) -> Optional[str]:
    """Extract references section from Markdown text (## TÀI LIỆU THAM KHẢO onwards)."""
    patterns = [
        r'##\s*TÀI LIỆU THAM KHẢO',
        r'##\s*TÀI LIỆU THAM KHẢO',
        r'##\s*REFERENCES',
        r'##\s*References',
    ]
    for pat in patterns:
        m = re.search(pat, md_text, re.IGNORECASE | re.UNICODE)
        if m:
            return md_text[m.start():]
    return None


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def print_statistics(doc: Document) -> None:
    """Print statistics about the built document."""
    h1_count = 0
    h2_count = 0
    h3_count = 0
    table_count = len(doc.tables)
    image_count = 0
    para_count = 0

    for para in doc.paragraphs:
        style_name = para.style.name if para.style else ""
        if style_name == "Heading 1":
            h1_count += 1
        elif style_name == "Heading 2":
            h2_count += 1
        elif style_name == "Heading 3":
            h3_count += 1
        elif style_name == "Normal":
            para_count += 1
        # Count inline images (runs with pictures)
        for run in para.runs:
            if run._r.findall('.//' + qn("a:blip"), namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}):
                image_count += 1

    # Count all blip references for images
    from lxml import etree
    blip_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
    all_blips = doc.element.body.findall(
        ".//{%s}blip" % blip_ns
    )
    image_count = len(all_blips)

    # Estimate page count (very rough: ~40 lines per page, avg para ~3 lines)
    est_pages = max(1, (para_count * 3 + h1_count * 2 + h2_count + table_count * 5) // 40)

    print("\n" + "=" * 60)
    print("THESIS DOCX BUILD STATISTICS")
    print("=" * 60)
    print(f"  Heading 1 (chapters/sections): {h1_count}")
    print(f"  Heading 2 (sub-sections):      {h2_count}")
    print(f"  Heading 3 (sub-sub-sections):  {h3_count}")
    print(f"  Tables:                        {table_count}")
    print(f"  Images:                        {image_count}")
    print(f"  Body paragraphs (Normal):      {para_count}")
    print(f"  Estimated pages:               ~{est_pages}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------
def build(template_path: str, out_path: str) -> None:
    print(f"[build] Template: {template_path}")
    print(f"[build] Output:   {out_path}")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Resolve repo root from out_path or cwd
    repo_root = Path(out_path).parent.parent.parent
    if not (repo_root / "docs").exists():
        repo_root = Path.cwd()

    thesis_v2 = repo_root / "docs" / "thesis-v2"
    figures_dir = thesis_v2 / "figures"

    # Pre-render Mermaid diagrams
    print("[build] Rendering Mermaid diagrams...")
    pngs = ensure_mermaid_pngs(figures_dir)
    if pngs:
        print(f"  Found/rendered {len(pngs)} diagram(s): {list(pngs.keys())}")

    # Prepare template
    print("[build] Preparing template...")
    doc = prepare_template(template_path)

    # ---- 1. Front matter (title page) ----
    front_matter_path = thesis_v2 / "front-matter.md"
    if front_matter_path.exists():
        print("[build] Adding front matter...")
        fm_text = front_matter_path.read_text(encoding="utf-8")
        add_front_matter(doc, fm_text)
    else:
        print("[build] WARNING: front-matter.md not found, skipping")

    # ---- 2. TOC ----
    print("[build] Adding MỤC LỤC...")
    _add_toc_field(doc, "MỤC LỤC", ' TOC \\o "1-3" \\h \\z \\u ')

    # ---- 3. List of Figures ----
    print("[build] Adding DANH MỤC HÌNH ẢNH...")
    _add_toc_field(doc, "DANH MỤC HÌNH ẢNH", f' TOC \\h \\z \\t "{CAPTION_FIGURE_STYLE},1" ')

    # ---- 4. List of Tables ----
    print("[build] Adding DANH MỤC BẢNG BIỂU...")
    _add_toc_field(doc, "DANH MỤC BẢNG BIỂU", f' TOC \\h \\z \\t "{CAPTION_TABLE_STYLE},1" ')

    # ---- 5. Chapters 1-2 ----
    ch12_path = repo_root / "docs" / "THESIS-CHAPTERS-1-2-WORKING-2026-09-26-VI.md"
    references_text: Optional[str] = None
    if ch12_path.exists():
        print(f"[build] Adding chapters 1-2 from {ch12_path.name}...")
        ch12_text = ch12_path.read_text(encoding="utf-8")
        references_text = extract_references(ch12_text)
        if references_text:
            ch12_text = ch12_text[:ch12_text.index(references_text)]
        # This file carries the thesis title as '#', chapters as '##' and sections as '###';
        # chapters 3-6 use '#' for chapters. Drop the title and promote one level.
        ch12_text = _shift_heading_levels(ch12_text, shift=1, drop_title=True)
        convert_markdown_to_doc(doc, ch12_text, is_first_chapter=True,
                                figures_dir=figures_dir, pngs=pngs)
    else:
        print(f"[build] WARNING: {ch12_path.name} not found")

    # ---- 6. Chapter 3 ----
    ch3_path = thesis_v2 / "chuong-3-phuong-phap.md"
    if ch3_path.exists():
        print(f"[build] Adding chapter 3 from {ch3_path.name}...")
        ch3_text = ch3_path.read_text(encoding="utf-8")
        convert_markdown_to_doc(doc, ch3_text, figures_dir=figures_dir, pngs=pngs)
    else:
        print(f"[build] WARNING: {ch3_path.name} not found, skipping")

    # ---- 7. Chapter 4 ----
    ch4_path = thesis_v2 / "chuong-4-thiet-ke-trien-khai.md"
    if ch4_path.exists():
        print(f"[build] Adding chapter 4 from {ch4_path.name}...")
        ch4_text = ch4_path.read_text(encoding="utf-8")
        convert_markdown_to_doc(doc, ch4_text, figures_dir=figures_dir, pngs=pngs)
    else:
        print(f"[build] WARNING: {ch4_path.name} not found, skipping")

    # ---- 7b. Product walkthrough section (part of chapter 4, no page break) ----
    for extra in sorted(thesis_v2.glob("chuong-4b-*.md")):
        print(f"[build] Adding {extra.name}...")
        convert_markdown_to_doc(doc, extra.read_text(encoding="utf-8"), figures_dir=figures_dir, pngs=pngs)

    # ---- 8. Chapters 5-6 (optional) ----
    for ch_glob_pattern in ["chuong-5-*.md", "chuong-6-*.md"]:
        # Only the rewritten chapters in docs/thesis-v2 are used; the older
        # THESIS-CHAPTERS-5-6 working file describes the pre-D-075 pipeline.
        found = list(thesis_v2.glob(ch_glob_pattern))
        if not found:
            print(f"[build] WARNING: No files matching {ch_glob_pattern} found, skipping")
            continue
        for ch_path in sorted(found):
            print(f"[build] Adding {ch_path.name}...")
            ch_text = ch_path.read_text(encoding="utf-8")
            convert_markdown_to_doc(doc, ch_text, figures_dir=figures_dir, pngs=pngs)

    # ---- 9. References ----
    if references_text:
        print("[build] Adding TÀI LIỆU THAM KHẢO...")
        # The section is written as '##' in the chapters 1-2 file; promote it to a chapter-level
        # heading (new page) and give every entry the APA hanging indent.
        first_ref = len(doc.paragraphs)
        convert_markdown_to_doc(doc, _shift_heading_levels(references_text, shift=1, drop_title=False),
                                figures_dir=figures_dir, pngs=pngs)
        for para in doc.paragraphs[first_ref:]:
            if para.style is not None and para.style.name == "Normal" and para.text.strip():
                pf = para.paragraph_format
                pf.left_indent = Cm(1.27)
                pf.first_line_indent = Cm(-1.27)
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # ---- Save ----
    settings_el = doc.settings.element
    if settings_el.find(qn("w:updateFields")) is None:
        upd = OxmlElement("w:updateFields")
        upd.set(qn("w:val"), "true")
        settings_el.append(upd)

    print(f"[build] Saving to {out}...")
    doc.save(str(out))
    print(f"[build] Done! File size: {out.stat().st_size / 1024:.1f} KB")

    if out.stat().st_size > 5 * 1024 * 1024:
        print(f"[build] NOTE: Output > 5 MB ({out.stat().st_size / 1024 / 1024:.1f} MB) — add to .gitignore")

    # Print statistics
    doc2 = Document(str(out))
    print_statistics(doc2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Build thesis Word document from Markdown sources.")
    parser.add_argument("--template", required=True, help="Path to the reference .docx template file.")
    parser.add_argument("--out", default="docs/thesis-v2/build/Khoa-luan.docx",
                        help="Output .docx path (default: docs/thesis-v2/build/Khoa-luan.docx)")
    args = parser.parse_args()

    if not Path(args.template).exists():
        print(f"ERROR: Template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    build(template_path=args.template, out_path=args.out)


if __name__ == "__main__":
    main()
