"""분석 파이프라인 통합: ``analyze(text) → Analysis``."""

from __future__ import annotations

from .clause_detector import detect_clauses
from .component_analyzer import analyze_components
from .models import Analysis
from .sentence_classifier import classify_sentence
from .tokenizer import tokenize


def analyze(text: str) -> Analysis:
    """입력 문장을 형태소 → 절 → 성분 → 문장 종류 순으로 분석한다."""

    text = (text or "").strip()
    eojeols = tokenize(text)
    root, notes = detect_clauses(eojeols)
    analyze_components(root, eojeols)
    sentence_type = classify_sentence(root)

    if any(c.kind == "PRED" for c in root.iter() if c is not root):
        notes.append("이중 주어 구문이 감지되어 서술절로 분석했습니다.")

    return Analysis(
        text=text,
        eojeols=eojeols,
        root=root,
        sentence_type=sentence_type,
        notes=notes,
    )
