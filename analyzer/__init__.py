"""한국어 통사 자동 분석 엔진.

규칙 기반 파이프라인:
    text -> tokenize -> detect_clauses -> analyze_components -> classify_sentence
"""

from .models import (
    Analysis,
    Clause,
    ClauseKind,
    Component,
    ComponentKind,
    Eojeol,
    Morph,
    SentenceType,
)
from .pipeline import analyze

__all__ = [
    "Analysis",
    "Clause",
    "ClauseKind",
    "Component",
    "ComponentKind",
    "Eojeol",
    "Morph",
    "SentenceType",
    "analyze",
]
