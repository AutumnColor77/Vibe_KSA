"""Streamlit UI: 한국어 통사 자동 분석기.

사이드바에서 예문을 고르거나 텍스트박스에 직접 입력해 「분석」 버튼을 누르면,
다음 네 개 탭을 통해 결과를 확인할 수 있다.

1. 요약 — 문장 종류와 안긴/이어진 절의 칩
2. 문장 성분 — 어절별 색상 강조
3. 절 구조 — graphviz 트리
4. 형태소 — Kiwi 분석 표
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from analyzer import analyze
from analyzer.llm_assistant import explain as llm_explain, is_available as llm_available
from analyzer.models import (
    CLAUSE_COLOR,
    CLAUSE_LABEL_KO,
    COMPONENT_COLOR,
    COMPONENT_LABEL_KO,
)
from analyzer.visualizer import (
    clause_tree_dot,
    component_highlight_html,
    morpheme_table_rows,
)


_APP_DIR = Path(__file__).resolve().parent
# 다른 폴더에서 `streamlit run …/streamlit_app.py` 를 실행해도 프로젝트 루트의 `.env` 를 읽도록 함
load_dotenv(_APP_DIR / ".env")
load_dotenv()
st.set_page_config(
    page_title="한국어 통사 자동 분석기",
    layout="wide",
)

EXAMPLES_PATH = Path(__file__).parent / "examples" / "sample_sentences.txt"


@st.cache_data
def _load_examples() -> list[tuple[str, str]]:
    if not EXAMPLES_PATH.exists():
        return []
    items: list[tuple[str, str]] = []
    for line in EXAMPLES_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|||" in line:
            label, sentence = line.split("|||", 1)
            items.append((label.strip(), sentence.strip()))
        else:
            items.append((line, line))
    return items


def _legend(mapping: dict[str, str], colors: dict[str, str], title: str) -> None:
    st.markdown(f"**{title}**")
    chips = []
    for kind, label in mapping.items():
        color = colors.get(kind, "#374151")
        chips.append(
            f'<span style="padding:2px 8px;margin:2px;border-radius:6px;'
            f'background:#fff;color:{color};border:1px solid {color};'
            f'display:inline-block;font-size:12px;">{label}</span>'
        )
    st.markdown(
        '<div style="line-height:2.2;">' + "".join(chips) + "</div>",
        unsafe_allow_html=True,
    )


def _render_summary(analysis) -> None:
    st.markdown(f"### {analysis.sentence_type.label}")

    if analysis.notes:
        with st.expander("분석 노트", expanded=False):
            for note in analysis.notes:
                st.markdown(f"- {note}")

    st.markdown("#### 안긴/이어진 절")
    chips = []
    for clause in analysis.all_clauses():
        if clause.kind == "MAIN":
            continue
        color = CLAUSE_COLOR.get(clause.kind, "#374151")
        head = ""
        if clause.head_eojeol_index is not None and 0 <= clause.head_eojeol_index < len(analysis.eojeols):
            head = analysis.eojeols[clause.head_eojeol_index].text
        body = (
            f"<b>{CLAUSE_LABEL_KO[clause.kind]}</b>"
            + (f" · 핵 ‘{head}’" if head else "")
            + (f" · {clause.note}" if clause.note else "")
        )
        chips.append(
            f'<div style="padding:8px 12px;margin:4px 0;border-radius:8px;'
            f'background:#fff;color:{color};border:1px solid {color};'
            f'display:block;">'
            f'{body}'
            f"</div>"
        )
    if chips:
        st.markdown("".join(chips), unsafe_allow_html=True)
    else:
        st.info("안긴 절이나 이어진 절이 없습니다 (홑문장).")


def _render_components(analysis) -> None:
    st.markdown("#### 문장 성분")
    st.markdown(component_highlight_html(analysis), unsafe_allow_html=True)

    rows = []
    for clause in analysis.all_clauses():
        for comp in clause.components:
            text = " ".join(analysis.eojeols[i].text for i in comp.eojeol_indices)
            rows.append(
                {
                    "절": CLAUSE_LABEL_KO[clause.kind],
                    "성분": COMPONENT_LABEL_KO[comp.kind],
                    "어절": text,
                    "근거": comp.note,
                }
            )
    if rows:
        st.markdown("##### 절별 성분 표")
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _render_tree(analysis) -> None:
    st.markdown("#### 절 구조 트리")
    st.graphviz_chart(clause_tree_dot(analysis), use_container_width=True)


def _render_morphs(analysis) -> None:
    st.markdown("#### 형태소 분석")
    rows = morpheme_table_rows(analysis)
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("분석된 형태소가 없습니다.")


def main() -> None:
    st.title("한국어 통사 자동 분석기")
    st.caption("Kiwi 형태소 분석 + 규칙 기반 통사 분석 (Streamlit). 옵션으로 Gemini 보조 설명.")

    examples = _load_examples()
    with st.sidebar:
        st.header("예문")
        labels = ["(직접 입력)"] + [f"{label}" for label, _ in examples]
        choice = st.selectbox("예문 선택", labels)
        chosen_text = ""
        if choice != "(직접 입력)":
            for label, sent in examples:
                if label == choice:
                    chosen_text = sent
                    break

        st.divider()
        st.header("AI 보조")
        ai_ready = llm_available()
        if not ai_ready:
            st.caption("Gemini API 키가 없어 AI 보조 설명은 비활성화되어 있습니다.")
            ai_on = False
        else:
            ai_on = st.toggle("Gemini 보조 설명 사용", value=False)

        st.divider()
        _legend(COMPONENT_LABEL_KO, COMPONENT_COLOR, "성분 색상")
        st.write("")
        _legend(CLAUSE_LABEL_KO, CLAUSE_COLOR, "절 종류 색상")

    default_text = st.session_state.get("input_text", chosen_text)
    if chosen_text and chosen_text != st.session_state.get("_last_choice"):
        default_text = chosen_text
        st.session_state["_last_choice"] = chosen_text

    text = st.text_area(
        "문장 입력",
        value=default_text,
        height=110,
        placeholder="예) 내가 어제 만난 사람은 친절하다.",
        key="input_text",
    )
    run = st.button("분석", type="primary")

    if run and text.strip():
        with st.spinner("분석 중…"):
            analysis = analyze(text)

        st.success("분석 완료")
        tab_summary, tab_comp, tab_tree, tab_morph = st.tabs(
            ["요약", "문장 성분", "절 구조", "형태소"]
        )
        with tab_summary:
            _render_summary(analysis)
        with tab_comp:
            _render_components(analysis)
        with tab_tree:
            _render_tree(analysis)
        with tab_morph:
            _render_morphs(analysis)

        if ai_on:
            with st.expander("AI 보조 설명 (Gemini)", expanded=True):
                with st.spinner("Gemini 호출 중…"):
                    md = llm_explain(analysis)
                st.markdown(md)


if __name__ == "__main__":
    main()
