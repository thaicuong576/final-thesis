"""Render the thesis Mermaid flowcharts to PNG without network access.

Supports the subset used in docs/thesis-v2/figures/*.mmd: ``flowchart TD|TB|LR``,
node shapes with quoted labels, chained edges (``A --> B --> C``), ``&`` groups,
``-->``, ``-.->``, ``<-->``, ``==>``, ``---``, edge labels (``-->|"x"|`` and
``-- x -->``), inline node definitions inside edges and ``subgraph ... end``.
Layout is a layered DAG (networkx) drawn with matplotlib.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

FONT = "DejaVu Sans"
NL = chr(10)
WRAP = 34
CHAR_W = 0.078  # inch per character at font size 9 (DejaVu Sans, bold titles)
LINE_H = 0.19  # inch per line

_OPEN = r"(?:\(\[|\[\[|\[\(|\(\(|\{\{|\[/|\[|\(|\{|>)"
_CLOSE = r"(?:\]\)|\]\]|\)\]|\)\)|\}\}|/\]|\]|\)|\})"
_NODE_QUOTED = re.compile(r'([A-Za-z_][\w]*)\s*' + _OPEN + r'\s*"(.*?)"\s*' + _CLOSE)
_NODE_PLAIN = re.compile(r'([A-Za-z_][\w]*)\s*' + _OPEN + r'([^"\[\]\(\)\{\}]*?)' + _CLOSE)
_EDGE_OP = re.compile(
    r'\s*(<-->|<-\.->|<==>|-\.->|==>|-->|-\.-|---)\s*(?:\|\s*"?(.*?)"?\s*\|)?\s*'
)
_TEXT_EDGE = re.compile(r'\s--\s*"?([^">-][^>]*?)"?\s*-->\s')


@dataclass
class Graph:
    direction: str = "TD"
    labels: dict[str, str] = field(default_factory=dict)
    edges: list[tuple[str, str, str, str]] = field(default_factory=list)  # src, dst, op, label
    groups: list[tuple[str, list[str]]] = field(default_factory=list)


def _clean_label(raw: str) -> str:
    s = raw.replace("&quot;", '"')
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</?(b|i|em|strong|u|small|span)[^>]*>", "", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip().strip('"').strip()


def parse_mermaid(text: str) -> Graph:
    g = Graph()
    stack: list[tuple[str, list[str]]] = []

    def register(node_id: str, label: str | None = None) -> None:
        if label is not None:
            g.labels[node_id] = _clean_label(label)
        g.labels.setdefault(node_id, node_id)
        if stack and node_id not in stack[-1][1]:
            stack[-1][1].append(node_id)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("%%") or line.startswith(("classDef", "class ", "style ", "linkStyle", "click ")):
            continue
        head = re.match(r"^(flowchart|graph)\s+(TD|TB|LR|RL|BT)", line)
        if head:
            g.direction = head.group(2)
            continue
        sub = re.match(r'^subgraph\s+(?:([\w-]+)\s*)?(?:\[\s*"?(.*?)"?\s*\]|"(.*?)"|(.*))?$', line)
        if sub:
            title = sub.group(2) or sub.group(3) or (sub.group(4) or "").strip() or sub.group(1) or ""
            stack.append((_clean_label(title), []))
            continue
        if line == "end":
            if stack:
                title, members = stack.pop()
                g.groups.append((title, members))
                if stack:
                    stack[-1][1].extend(m for m in members if m not in stack[-1][1])
            continue
        if line.startswith("direction "):
            continue

        # Replace inline node definitions by their ids, remembering labels.
        def sub_quoted(m: re.Match) -> str:
            register(m.group(1), m.group(2))
            return m.group(1)

        def sub_plain(m: re.Match) -> str:
            register(m.group(1), m.group(2))
            return m.group(1)

        saved: list[str] = []

        def protect(m: re.Match) -> str:
            saved.append(m.group(1))
            return f"|@@{len(saved) - 1}@@|"

        line = re.sub(r'\|\s*"?([^|]*?)"?\s*\|', protect, line)
        line = _NODE_QUOTED.sub(sub_quoted, line)
        line = _NODE_PLAIN.sub(sub_plain, line)
        line = re.sub(r"\|@@(\d+)@@\|", lambda m: '|"' + saved[int(m.group(1))] + '"|', line)
        line = _TEXT_EDGE.sub(lambda m: f' -->|{m.group(1)}| ', f" {line} ").strip()

        parts = _EDGE_OP.split(line)
        # parts = [nodes, op, label, nodes, op, label, nodes, ...]
        if len(parts) == 1:
            for nid in re.split(r"\s*&\s*", parts[0].strip()):
                if re.fullmatch(r"[A-Za-z_][\w]*", nid):
                    register(nid)
            continue
        node_groups = parts[0::3]
        ops = parts[1::3]
        labels = parts[2::3]
        ids_per_group = [
            [n for n in re.split(r"\s*&\s*", grp.strip()) if re.fullmatch(r"[A-Za-z_][\w]*", n)]
            for grp in node_groups
        ]
        for ids in ids_per_group:
            for nid in ids:
                register(nid)
        for k, op in enumerate(ops):
            for src in ids_per_group[k]:
                for dst in ids_per_group[k + 1] if k + 1 < len(ids_per_group) else []:
                    g.edges.append((src, dst, op, _clean_label(labels[k] or "")))
    for title, members in stack:
        g.groups.append((title, members))
    return g


def _wrap(label: str, wrap: int = WRAP) -> tuple[str, str]:
    lines = [ln.strip() for ln in label.split("\n") if ln.strip()]
    if not lines:
        return "", ""
    title = "\n".join(textwrap.wrap(lines[0], WRAP)) or lines[0]
    body_lines: list[str] = []
    for ln in lines[1:]:
        body_lines.extend(textwrap.wrap(ln, wrap + 6, subsequent_indent="  ") or [ln])
    return title, "\n".join(body_lines)


def _layers(g: Graph) -> dict[str, int]:
    dg = nx.DiGraph()
    dg.add_nodes_from(g.labels)
    for s, d, _, _ in g.edges:
        if s != d:
            dg.add_edge(s, d)
    dag = nx.DiGraph(dg)
    while not nx.is_directed_acyclic_graph(dag):
        cycle = nx.find_cycle(dag)
        dag.remove_edge(*cycle[-1][:2])
    layer: dict[str, int] = {}
    for node in nx.topological_sort(dag):
        preds = list(dag.predecessors(node))
        layer[node] = 0 if not preds else max(layer[p] for p in preds) + 1
    return layer


MAX_PER_ROW = 4
MAX_LAYERS_PER_COLUMN = 5
TARGET_ASPECT = 0.85  # width / height, roughly a portrait text block


def _group_layers(g: Graph) -> dict[str, int] | None:
    """Tiered diagrams: >= 3 top-level subgraphs covering every node -> one tier per subgraph."""
    tops = [(t, m) for t, m in g.groups if m]
    # keep only groups that are not contained in another group
    tops = [(t, m) for t, m in tops if not any(set(m) < set(o) for _, o in tops)]
    covered = {n for _, m in tops for n in m}
    if len(tops) < 3 or covered != set(g.labels):
        return None
    order = sorted(range(len(tops)), key=lambda i: min(list(g.labels).index(n) for n in tops[i][1]))
    return {n: rank for rank, i in enumerate(order) for n in tops[i][1]}


def _layout(g: Graph, compact: bool, horizontal: bool, wrap: int = WRAP, per_row: int = MAX_PER_ROW,
            allow_fold: bool = True):
    layer = _group_layers(g) or _layers(g)
    sizes: dict[str, tuple[float, float, str, str]] = {}
    for nid, label in g.labels.items():
        title, body = _wrap(label, wrap)
        if compact:
            body = ""
        lines = [*title.split(NL), *(body.split(NL) if body else [])]
        width = max(1.2, max(len(ln) for ln in lines) * CHAR_W + 0.3)
        height = len(lines) * LINE_H + 0.3
        sizes[nid] = (width, height, title, body)

    by_layer: dict[int, list[str]] = {}
    for nid in g.labels:
        by_layer.setdefault(layer.get(nid, 0), []).append(nid)
    order = {nid: i for lst in by_layer.values() for i, nid in enumerate(lst)}
    for _ in range(2):
        for lvl in sorted(by_layer):
            def bary(n: str, lvl: int = lvl) -> float:
                ps = [order[s] for s, d, _, _ in g.edges if d == n and layer.get(s, 0) < lvl]
                return sum(ps) / len(ps) if ps else order[n]
            by_layer[lvl].sort(key=bary)
            for i, n in enumerate(by_layer[lvl]):
                order[n] = i

    # Wide layers wrap into several rows; each row becomes its own visual level.
    rows: list[list[str]] = []
    rank: dict[str, int] = {}
    for lvl in sorted(by_layer):
        nodes = by_layer[lvl]
        for k in range(0, len(nodes), per_row):
            for n in nodes[k:k + per_row]:
                rank[n] = len(rows)
            rows.append(nodes[k:k + per_row])

    # Long chains fold into several columns ("snake"), so the figure stays near page shape.
    n_cols = max(1, -(-len(rows) // MAX_LAYERS_PER_COLUMN)) if allow_fold and len(rows) > MAX_LAYERS_PER_COLUMN + 1 else 1
    per_col = -(-len(rows) // n_cols)
    gap_main, gap_cross, gap_col = 0.7, 0.35, 1.0
    pos: dict[str, tuple[float, float]] = {}
    col_cross_offset = 0.0
    for c in range(n_cols):
        col_rows = rows[c * per_col:(c + 1) * per_col]
        if not col_rows:
            break
        widths = []
        for row in col_rows:
            widths.append(sum((sizes[n][1] if horizontal else sizes[n][0]) for n in row) + gap_cross * (len(row) - 1))
        col_width = max(widths)
        main_offset = 0.0
        for row, row_width in zip(col_rows, widths):
            main_extent = max((sizes[n][0] if horizontal else sizes[n][1]) for n in row)
            cursor = col_cross_offset + (col_width - row_width) / 2
            for n in row:
                cross = sizes[n][1] if horizontal else sizes[n][0]
                center_cross = cursor + cross / 2
                center_main = main_offset + main_extent / 2
                pos[n] = (center_main, -center_cross) if horizontal else (center_cross, -center_main)
                cursor += cross + gap_cross
            main_offset += main_extent + gap_main
        col_cross_offset += col_width + gap_col
    xs = [pos[n][0] - sizes[n][0] / 2 for n in pos] + [pos[n][0] + sizes[n][0] / 2 for n in pos]
    ys = [pos[n][1] - sizes[n][1] / 2 for n in pos] + [pos[n][1] + sizes[n][1] / 2 for n in pos]
    return pos, sizes, rank, (max(xs) - min(xs) + 1.2, max(ys) - min(ys) + 1.2)


def render(mmd_path: Path, png_path: Path) -> Path:
    import math

    g = parse_mermaid(mmd_path.read_text(encoding="utf-8"))
    original_horizontal = g.direction in ("LR", "RL")
    # Pick the layout whose text stays largest once scaled into the page text block
    # (about 6.3 x 9 inches; 9pt design text may shrink to ~70%).
    page_w, page_h = 6.3 / 0.72, 9.0 / 0.72
    best = None
    for horizontal in (original_horizontal, not original_horizontal):
        for wrap in (WRAP, 24, 18):
          for per_row in (MAX_PER_ROW, 3, 2):
            for compact in (False, True):
              for fold in (False, True):
                pos, sizes, rank, (w, h) = _layout(g, compact, horizontal, wrap, per_row, fold)
                scale = min(page_w / w, page_h / h, 1.0)
                score = -scale + (0.12 if compact else 0.0) + (0.03 if horizontal != original_horizontal else 0.0)                     + (0.01 if wrap != WRAP else 0.0) + (0.25 if fold else 0.0)
                if best is None or score < best[0]:
                    best = (score, pos, sizes, rank, horizontal)
    _, pos, sizes, layer, horizontal = best

    xs = [pos[n][0] - sizes[n][0] / 2 for n in pos] + [pos[n][0] + sizes[n][0] / 2 for n in pos]
    ys = [pos[n][1] - sizes[n][1] / 2 for n in pos] + [pos[n][1] + sizes[n][1] / 2 for n in pos]
    pad = 0.6
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    fig_w, fig_h = x1 - x0, y1 - y0
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.axis("off")

    palette = ["#eef4fb", "#f3f7ee", "#fbf3ea", "#f4eff9", "#eef7f6", "#f9eef1"]
    for gi, (title, members) in enumerate(g.groups):
        members = [m for m in members if m in pos]
        if not members:
            continue
        gx0 = min(pos[m][0] - sizes[m][0] / 2 for m in members) - 0.18
        gx1 = max(pos[m][0] + sizes[m][0] / 2 for m in members) + 0.18
        gy0 = min(pos[m][1] - sizes[m][1] / 2 for m in members) - 0.18
        gy1 = max(pos[m][1] + sizes[m][1] / 2 for m in members) + 0.38
        ax.add_patch(FancyBboxPatch((gx0, gy0), gx1 - gx0, gy1 - gy0, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc=palette[gi % len(palette)], ec="#9aa7b4", lw=0.8, ls="--", zorder=0))
        if title:
            ax.text(gx0 + 0.1, gy1 - 0.08, "\n".join(textwrap.wrap(title, 60)), ha="left", va="top",
                    fontsize=8, fontweight="bold", color="#44515e", family=FONT, zorder=1)

    for nid, (x, y) in pos.items():
        w, h, title, body = sizes[nid]
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                    fc="white", ec="#2f6fa8", lw=1.1, zorder=2))
        top = y + h / 2 - 0.15
        ax.text(x, top, title, ha="center", va="top", fontsize=9, fontweight="bold", family=FONT, zorder=3,
                linespacing=1.15)
        if body:
            n_title = title.count("\n") + 1
            ax.text(x - w / 2 + 0.15, top - n_title * LINE_H - 0.04, body, ha="left", va="top", fontsize=8,
                    family=FONT, zorder=3, linespacing=1.2, color="#222")

    def border_point(n: str, tx: float, ty: float) -> tuple[float, float]:
        x, y = pos[n]
        w, h = sizes[n][0] / 2, sizes[n][1] / 2
        dx, dy = tx - x, ty - y
        if dx == 0 and dy == 0:
            return x, y
        scale = min(w / abs(dx) if dx else float("inf"), h / abs(dy) if dy else float("inf"))
        return x + dx * scale, y + dy * scale

    for src, dst, op, label in g.edges:
        if src not in pos or dst not in pos or src == dst:
            continue
        back = layer.get(dst, 0) <= layer.get(src, 0)
        p0 = border_point(src, *pos[dst])
        p1 = border_point(dst, *pos[src])
        style = "<|-|>" if op.startswith("<") else ("-" if op in ("---", "-.-") else "-|>")
        ls = "--" if "." in op else "-"
        lw = 1.6 if op.startswith("==") else 1.0
        arrow = FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=11, lw=lw, ls=ls, color="#44515e",
                                connectionstyle=f"arc3,rad={-0.6 if back else 0.0}", zorder=1.5)
        ax.add_patch(arrow)
        if label:
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            if back:
                mx += 0.9 if not horizontal else 0.0
                my += 0.0 if not horizontal else 0.9
            ax.text(mx, my, "\n".join(textwrap.wrap(label, 28)), ha="center", va="center", fontsize=7.5,
                    family=FONT, color="#1f3b57", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))

    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=200, facecolor="white")
    plt.close(fig)
    return png_path


if __name__ == "__main__":
    import sys

    for arg in sys.argv[1:]:
        src = Path(arg)
        print(render(src, src.with_suffix(".png")))
