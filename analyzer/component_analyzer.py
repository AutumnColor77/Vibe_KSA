"""문장 성분(주어·서술어·목적어·보어·관형어·부사어·독립어) 분석.

각 ``Clause`` 의 ‘직속 어절’(자식 절에 속하지 않는 어절들)에 대해 성분을 부착한다.
또한 자식 절은 모절에서 어떤 역할을 하는지 ``Clause.role`` 로 기록하고, 모절의
``components`` 에도 그 자식 절을 단일 성분으로 등록한다.
"""

from __future__ import annotations

from typing import Optional

from .models import (
    CLAUSE_LABEL_KO,
    COMPONENT_LABEL_KO,
    Clause,
    Component,
    ComponentKind,
    Eojeol,
)


_PREDICATE_BASE_TAGS = {"VV", "VA", "VX", "VCP", "VCN"}
_NOUN_BASE_TAGS = {"NNG", "NNP", "NP", "NR", "NNB", "SL", "SH", "SN"}


def _base_tag(tag: str) -> str:
    """Kiwi 의 ``VV-I`` / ``VA-R`` 같은 접미를 떼고 기본 태그만 반환."""

    return tag.split("-", 1)[0]


def _is_predicate(tag: str) -> bool:
    return _base_tag(tag) in _PREDICATE_BASE_TAGS


def _is_noun(tag: str) -> bool:
    return _base_tag(tag) in _NOUN_BASE_TAGS


def _eo_has_predicate_like(eo: Eojeol) -> bool:
    """VV/VA/… 외에 ‘친절하다’류 XSA+EF, ‘말했다’류 XSV+EP 도 서술어로 본다."""

    tags = [m.tag for m in eo.morphs]
    if any(_is_predicate(t) for t in tags):
        return True
    bases = {_base_tag(t) for t in tags}
    if bases & {"XSA", "XSV"}:
        if any(_base_tag(t) in ("EF", "EP") for t in tags):
            return True
    return False


def _direct_indices(clause: Clause) -> list[int]:
    """이 절의 직속 어절 인덱스 (자식 절의 span 안에 있는 어절은 제외)."""

    consumed: set[int] = set()
    for child in clause.children:
        for k in range(child.span[0], child.span[1] + 1):
            consumed.add(k)
    return [
        i
        for i in range(clause.span[0], clause.span[1] + 1)
        if i not in consumed
    ]


def _classify_eojeol(
    eo: Eojeol,
    is_head: bool,
    next_eo: Optional[Eojeol],
) -> tuple[Optional[ComponentKind], str]:
    """단일 어절의 성분과 부연을 추정.

    절의 head 어절은 우선적으로 서술어 후보로 본다. head 가 아니거나 head 라도
    용언 성분이 없을 때는 격조사/품사 기반으로 판정한다.
    """

    morphs = eo.morphs
    if not morphs:
        return None, ""

    has_predicate = _eo_has_predicate_like(eo)

    if is_head and has_predicate:
        return "PRED", "절의 서술어"

    if is_head and not has_predicate:
        # NNB + 격조사 같은 ‘의존명사 명사절 head’: 절 내부에서는 별도 라벨을
        # 달지 않고, 모절의 성분(예: 주어/목적어)으로만 잡힌다.
        return None, ""

    if any(m.tag == "JKQ" for m in morphs):
        return "ADV", "인용격조사 (인용절을 안고 있음)"

    for m in morphs:
        if m.tag == "JKS":
            return "SUBJ", f"주격조사 ‘{m.surface}’"
        if m.tag == "JKO":
            return "OBJ", f"목적격조사 ‘{m.surface}’"
        if m.tag == "JKC":
            return "COMPL", f"보격조사 ‘{m.surface}’"
        if m.tag == "JKB":
            return "ADV", f"부사격조사 ‘{m.surface}’"
        if m.tag == "JKG":
            return "ADN", f"관형격조사 ‘{m.surface}’"
        if m.tag == "JKV":
            return "INDEP", f"호격조사 ‘{m.surface}’"

    last = morphs[-1]
    if last.tag == "ETM":
        return "ADN", f"관형사형 전성어미 ‘{last.surface}’"

    if any(m.tag == "MM" for m in morphs):
        return "ADN", "관형사"

    if any(m.tag in ("MAG", "MAJ") for m in morphs):
        return "ADV", "부사"

    if any(m.tag == "IC" for m in morphs):
        return "INDEP", "감탄사"

    for m in morphs:
        if m.tag == "JX":
            if any(_is_noun(mm.tag) for mm in morphs):
                lemma = m.lemma
                if lemma in {"은", "는"}:
                    return "SUBJ", f"보조사 ‘{m.surface}’ (주어 또는 주제)"
                if lemma in {"도", "만", "조차", "마저", "까지", "부터"}:
                    return "SUBJ", f"보조사 ‘{m.surface}’ (격조사 생략, 주어 추정)"
                return "SUBJ", f"보조사 ‘{m.surface}’"

    if has_predicate:
        return "PRED", "용언 (서술어 추정)"

    if any(_is_noun(m.tag) for m in morphs):
        if next_eo is not None and _eo_has_predicate_like(next_eo):
            return "OBJ", "체언 (격조사 생략, 목적어 추정)"
        return "SUBJ", "체언 (격조사 생략, 주어 추정)"

    return None, ""


def _determine_child_role(child: Clause, eojeols: list[Eojeol]) -> Optional[ComponentKind]:
    """자식 절이 모절에서 담당하는 성분(역할)."""

    if child.kind == "ADN":
        return "ADN"
    if child.kind == "ADV":
        return "ADV"
    if child.kind == "PRED":
        return "PRED"
    if child.kind in ("COORD", "SUBORD"):
        return None
    if child.kind in ("NOUN", "QUOT"):
        head = child.head_eojeol_index
        if head is None or not (0 <= head < len(eojeols)):
            return None
        eo = eojeols[head]
        for m in eo.morphs:
            if m.tag == "JKS":
                return "SUBJ"
            if m.tag == "JKO":
                return "OBJ"
            if m.tag == "JKC":
                return "COMPL"
            if m.tag == "JKB":
                return "ADV"
            if m.tag == "JKG":
                return "ADN"
            if m.tag == "JKQ":
                return "ADV"
        if any(
            m.tag == "JX"
            and m.lemma in {"은", "는", "도", "만", "조차", "마저", "까지", "부터"}
            for m in eo.morphs
        ):
            return "SUBJ"
        if child.kind == "QUOT":
            return "ADV"
        return None
    return None


def _post_adjust_complement(
    components: list[Component], eojeols: list[Eojeol]
) -> None:
    """‘이/가’ 가 ‘되다/아니다’ 앞에 오면 보어로 재분류한다."""

    pred_idx: Optional[int] = None
    for idx, comp in enumerate(components):
        if comp.kind == "PRED":
            pred_idx = idx
    if pred_idx is None:
        return
    pred_comp = components[pred_idx]
    pred_eojeol = eojeols[pred_comp.eojeol_indices[0]]
    pred_lemma = ""
    for m in pred_eojeol.morphs:
        if _is_predicate(m.tag) or _base_tag(m.tag) in ("XSA", "XSV"):
            pred_lemma = m.lemma
            break
    if pred_lemma not in {"되", "아니"}:
        return
    for idx in range(pred_idx - 1, -1, -1):
        comp = components[idx]
        if comp.kind != "SUBJ":
            continue
        eo = eojeols[comp.eojeol_indices[0]]
        if any(m.tag == "JKS" and m.surface in {"이", "가"} for m in eo.morphs):
            comp.kind = "COMPL"
            comp.note = (
                comp.note + " · 보어로 재분류 (‘되다/아니다’ 앞)"
            ).strip(" ·")
            return


def analyze_components(clause: Clause, eojeols: list[Eojeol]) -> None:
    """절 트리를 재귀적으로 순회하며 각 절에 ``components`` 를 채운다."""

    for child in clause.children:
        analyze_components(child, eojeols)
        child.role = _determine_child_role(child, eojeols)

    direct = _direct_indices(clause)
    head_idx = clause.head_eojeol_index
    components: list[Component] = []

    direct_set = set(direct)
    indices_in_order: list[tuple[str, int, Optional[Clause]]] = []
    seen_children: set[int] = set()
    for i in range(clause.span[0], clause.span[1] + 1):
        if i in direct_set:
            indices_in_order.append(("E", i, None))
        else:
            for ci, child in enumerate(clause.children):
                if ci in seen_children:
                    continue
                if child.span[0] <= i <= child.span[1]:
                    indices_in_order.append(("C", ci, child))
                    seen_children.add(ci)
                    break

    flat_direct_order = [i for kind, i, _c in indices_in_order if kind == "E"]
    for pos, idx in enumerate(flat_direct_order):
        eo = eojeols[idx]
        next_eo = None
        if pos + 1 < len(flat_direct_order):
            next_eo = eojeols[flat_direct_order[pos + 1]]
        kind, note = _classify_eojeol(
            eo,
            is_head=(idx == head_idx),
            next_eo=next_eo,
        )
        if kind is None:
            continue
        components.append(
            Component(kind=kind, eojeol_indices=[idx], note=note)
        )

    for child in clause.children:
        if child.role is None:
            continue
        components.append(
            Component(
                kind=child.role,
                eojeol_indices=list(range(child.span[0], child.span[1] + 1)),
                note=(
                    f"{CLAUSE_LABEL_KO[child.kind]}이(가) "
                    f"{COMPONENT_LABEL_KO[child.role]} 자리에 들어감"
                ),
            )
        )

    components.sort(key=lambda c: (c.eojeol_indices[0], c.eojeol_indices[-1]))
    _post_adjust_complement(components, eojeols)
    clause.components = components
