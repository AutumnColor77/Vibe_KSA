"""절 트리/문장 성분 시각화 (graphviz DOT, HTML 하이라이트)."""

from __future__ import annotations

import html as _html
from typing import Iterable

from .models import (
    CLAUSE_COLOR,
    CLAUSE_LABEL_KO,
    COMPONENT_COLOR,
    COMPONENT_LABEL_KO,
    Analysis,
    Clause,
    Component,
    ComponentKind,
    Eojeol,
)


def clause_tree_dot(analysis: Analysis) -> str:
    """절 트리를 graphviz DOT 문자열로 변환."""

    lines: list[str] = ["digraph clauses {", '  rankdir=TB;', '  node [shape=box, style="rounded,filled", fontname="Malgun Gothic"];']
    counter = {"n": 0}
    eojeols = analysis.eojeols

    def add_node(clause: Clause) -> str:
        counter["n"] += 1
        node_id = f"c{counter['n']}"
        span_text = _span_text(clause, eojeols)
        if clause.head_eojeol_index is not None and 0 <= clause.head_eojeol_index < len(eojeols):
            head_text = eojeols[clause.head_eojeol_index].text
        else:
            head_text = ""
        marker = clause.marker_morph
        marker_text = (
            f"표지: {marker.surface}/{marker.tag}" if marker is not None else ""
        )
        body_lines = [
            f"<b>{_html.escape(CLAUSE_LABEL_KO[clause.kind])}</b>",
        ]
        if head_text:
            body_lines.append(
                f"핵: <font color='#111827'><b>{_html.escape(head_text)}</b></font>"
            )
        if clause.note:
            body_lines.append(_html.escape(clause.note))
        if marker_text:
            body_lines.append(_html.escape(marker_text))
        if span_text:
            body_lines.append(
                f"<font point-size='10' color='#374151'>{_html.escape(span_text)}</font>"
            )
        label = "<" + "<br/>".join(body_lines) + ">"
        color = CLAUSE_COLOR.get(clause.kind, "#1f2937")
        fill = _light_fill(color)
        lines.append(
            f'  {node_id} [label={label}, color="{color}", fillcolor="{fill}", fontcolor="{color}"];'
        )
        for child in clause.children:
            child_id = add_node(child)
            lines.append(f"  {node_id} -> {child_id};")
        return node_id

    add_node(analysis.root)
    lines.append("}")
    return "\n".join(lines)


def component_highlight_html(analysis: Analysis) -> str:
    """어절별 문장 성분 색상 강조 HTML.

    한 어절이 여러 절에서 성분으로 잡혀 있으면 (예: 안긴 절 안의 주어이자
    동시에 모절의 목적어 명사절의 일부), 가장 안쪽(span 길이가 짧은) 절의
    성분 라벨을 우선한다.
    """

    eojeols = analysis.eojeols
    eo_to_component: dict[int, tuple[Component, Clause]] = {}
    for clause in analysis.all_clauses():
        clause_size = clause.span[1] - clause.span[0]
        for comp in clause.components:
            for idx in comp.eojeol_indices:
                if idx in eo_to_component:
                    _existing_comp, existing_clause = eo_to_component[idx]
                    existing_size = existing_clause.span[1] - existing_clause.span[0]
                    if existing_size <= clause_size:
                        continue
                eo_to_component[idx] = (comp, clause)

    chips: list[str] = []
    for eo in eojeols:
        entry = eo_to_component.get(eo.index)
        text = _html.escape(eo.text)
        if entry is None:
            chips.append(
                f'<span style="padding:4px 6px;margin:2px;border-radius:6px;'
                f'background:#f3f4f6;color:#374151;display:inline-block;">{text}</span>'
            )
            continue
        comp, _clause = entry
        color = COMPONENT_COLOR.get(comp.kind, "#374151")
        label = COMPONENT_LABEL_KO.get(comp.kind, comp.kind)
        chips.append(
            f'<span title="{_html.escape(comp.note)}" '
            f'style="padding:4px 8px;margin:2px;border-radius:6px;'
            f'background:{_light_fill(color)};color:{color};border:1px solid {color};'
            f'display:inline-block;font-weight:600;">'
            f'{text}<sub style="font-weight:500;font-size:10px;margin-left:4px;">{label}</sub>'
            f"</span>"
        )

    legend = _legend_html()
    return (
        '<div style="line-height:2;font-size:16px;font-family:\'Malgun Gothic\',sans-serif;">'
        + "".join(chips)
        + "</div>"
        + legend
    )


def morpheme_table_rows(analysis: Analysis) -> list[dict[str, str]]:
    """``st.dataframe`` 용 형태소 테이블."""

    rows: list[dict[str, str]] = []
    for eo in analysis.eojeols:
        for m in eo.morphs:
            rows.append(
                {
                    "어절": eo.text,
                    "형태소": m.surface,
                    "기본형": m.lemma,
                    "품사": m.tag,
                    "품사 해설": _tag_explain(m.tag),
                }
            )
    return rows


def _span_text(clause: Clause, eojeols: list[Eojeol]) -> str:
    a, b = clause.span
    if not eojeols:
        return ""
    a = max(0, a)
    b = min(len(eojeols) - 1, b)
    if a > b:
        return ""
    return " ".join(eo.text for eo in eojeols[a : b + 1])


def _light_fill(hex_color: str) -> str:
    """HEX 색을 옅은 배경으로 변환 (단순한 lighten)."""

    if not hex_color.startswith("#") or len(hex_color) != 7:
        return "#f3f4f6"
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = r + (255 - r) * 85 // 100
    g = g + (255 - g) * 85 // 100
    b = b + (255 - b) * 85 // 100
    return f"#{r:02x}{g:02x}{b:02x}"


def _legend_html() -> str:
    items = []
    for kind, label in COMPONENT_LABEL_KO.items():
        color = COMPONENT_COLOR[kind]
        items.append(
            f'<span style="padding:2px 6px;margin:2px;border-radius:4px;'
            f'background:{_light_fill(color)};color:{color};border:1px solid {color};'
            f'display:inline-block;font-size:12px;">{label}</span>'
        )
    return (
        '<div style="margin-top:12px;font-size:13px;color:#6b7280;">'
        + "범례: "
        + "".join(items)
        + "</div>"
    )


_TAG_HUMAN: dict[str, str] = {
    "NNG": "일반 명사",
    "NNP": "고유 명사",
    "NNB": "의존 명사",
    "NR": "수사",
    "NP": "대명사",
    "VV": "동사",
    "VA": "형용사",
    "VX": "보조 용언",
    "VCP": "긍정 지정사 (이다)",
    "VCN": "부정 지정사 (아니다)",
    "MM": "관형사",
    "MAG": "일반 부사",
    "MAJ": "접속 부사",
    "IC": "감탄사",
    "JKS": "주격 조사",
    "JKC": "보격 조사",
    "JKG": "관형격 조사",
    "JKO": "목적격 조사",
    "JKB": "부사격 조사",
    "JKV": "호격 조사",
    "JKQ": "인용격 조사",
    "JC": "접속 조사",
    "JX": "보조사",
    "EP": "선어말 어미",
    "EF": "종결 어미",
    "EC": "연결 어미",
    "ETN": "명사형 전성어미",
    "ETM": "관형사형 전성어미",
    "XPN": "체언 접두사",
    "XSN": "명사 파생 접미사",
    "XSV": "동사 파생 접미사",
    "XSA": "형용사 파생 접미사",
    "XR": "어근",
    "SF": "마침표/물음표/느낌표",
    "SP": "쉼표",
    "SS": "따옴표·괄호",
    "SE": "줄임표",
    "SO": "붙임표",
    "SW": "기타 기호",
    "SH": "한자",
    "SL": "외국어",
    "SN": "숫자",
    "UNK": "미상",
}


def _tag_explain(tag: str) -> str:
    return _TAG_HUMAN.get(tag, tag)
