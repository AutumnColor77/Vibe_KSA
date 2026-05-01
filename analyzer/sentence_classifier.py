"""문장 종류(홑/겹문장 + 안은문장·이어진문장) 분류."""

from __future__ import annotations

from .models import CLAUSE_LABEL_KO, Clause, ClauseKind, SentenceType


_EMBEDDED_KINDS: set[str] = {"NOUN", "ADN", "ADV", "PRED", "QUOT"}
_CONJOINED_KINDS: set[str] = {"COORD", "SUBORD"}


def _collect_kinds(root: Clause) -> list[ClauseKind]:
    kinds: list[ClauseKind] = []
    for c in root.iter():
        if c.kind == "MAIN":
            continue
        kinds.append(c.kind)
    return kinds


def classify_sentence(root: Clause) -> SentenceType:
    kinds = _collect_kinds(root)
    embedded = [k for k in kinds if k in _EMBEDDED_KINDS]
    conjoined = [k for k in kinds if k in _CONJOINED_KINDS]

    has_embedded = bool(embedded)
    has_conjoined = bool(conjoined)
    simple = not (has_embedded or has_conjoined)

    embedded_unique: list[ClauseKind] = []
    for k in embedded:
        if k not in embedded_unique:
            embedded_unique.append(k)

    conjoined_kind: ClauseKind | None = None
    if conjoined:
        # SUBORD 가 하나라도 있으면 종속, 모두 COORD 면 대등
        if any(k == "SUBORD" for k in conjoined):
            conjoined_kind = "SUBORD"
        else:
            conjoined_kind = "COORD"

    parts: list[str] = []
    if simple:
        parts.append("홑문장")
    else:
        parts.append("겹문장")
        if has_embedded:
            embedded_label = ", ".join(CLAUSE_LABEL_KO[k] for k in embedded_unique)
            parts.append(f"안은 문장 ({embedded_label}을(를) 안음)")
        if has_conjoined:
            parts.append(
                "이어진 문장 (대등)" if conjoined_kind == "COORD" else "이어진 문장 (종속)"
            )

    label = " · ".join(parts)
    return SentenceType(
        simple=simple,
        has_embedded=has_embedded,
        has_conjoined=has_conjoined,
        embedded_kinds=embedded_unique,
        conjoined_kind=conjoined_kind,
        label=label,
    )
