"""안긴문장(명사·관형·부사·서술·인용절)과 이어진 문장(대등/종속) 식별.

전략은 PLAN.md §4.2 와 동일하다. Kiwi POS 태그를 기반으로 어절별 트리거를
탐지하고, 트리거가 있는 어절을 head로 하는 ``Clause`` 노드를 생성한다.
모든 절은 임시로 span=(0, head_index)로 두고, 마지막에 head_index 의
포함 관계로 부모-자식 트리를 구성한다.
"""

from __future__ import annotations

from typing import Optional

from .models import Clause, Eojeol, Morph


def _base_tag(tag: str) -> str:
    return tag.split("-", 1)[0]


# 부사형 전성어미 후보 (학교 문법: 부사절을 만든다)
_ADV_EC_LEMMAS: set[str] = {"게", "도록", "듯이", "듯", "토록"}

# 대등 연결어미
_COORD_EC_LEMMAS: set[str] = {
    "고", "며", "으며", "나", "으나", "거나", "든지", "든가", "든",
}

# 종속 연결어미
_SUBORD_EC_LEMMAS: set[str] = {
    "면", "으면", "니", "으니", "아서", "어서", "여서", "라서", "이라서",
    "므로", "으므로", "려고", "으려고", "러", "으러",
    "자", "자마자", "는데", "ㄴ데", "은데",
    "ㄹ수록", "을수록", "수록",
    "거든", "다가", "어야", "아야", "여야",
    "고자", "도록",  # 일부 종속용법
    "지만", "건만", "더라도", "어도", "아도",
}

# 간접 인용 EC 어미 (Kiwi 가 "-ㄴ다고" 등을 한 형태소로 잡는 케이스 대응)
_INDIRECT_QUOTE_EC_LEMMAS: set[str] = {
    "고",
    "ㄴ다고", "는다고", "다고", "라고", "이라고",
    "자고", "냐고", "느냐고", "으냐고",
    # Kiwi 가 종종 초성 ‘ㄴ’ 대신 낱글자 ‘ᆫ’ 조합으로 lemma 를 줄 때
    "ᆫ다고",
}

# 명사절 ‘~는 것/줄/바/데/수/리’ 류 의존명사
_NOUN_CLAUSE_DEP_NOUNS: set[str] = {"것", "바", "줄", "데"}

# 간접 인용: ‘-(는/ㄴ)다고/-라고/-자고/-(느)냐고’ 뒤에 오는 발화·사유 동사
_SPEECH_VERB_LEMMAS: set[str] = {
    "말하", "이야기하", "주장하", "생각하", "여기", "믿", "보",
    "외치", "대답하", "묻", "듣", "느끼", "알", "전하", "쓰", "적", "하",
}

# 동격 관형절 표지: 인용형이 그대로 관형형 어미로 활용된 형태
_APPOSITIVE_ETM_FORMS: set[str] = {"다는", "라는", "자는", "냐는", "느냐는", "라던"}

# 명사절 NNB 의 격조사 화이트리스트 (격조사 + 보조사)
_NOMINAL_CASE_TAGS: set[str] = {"JKS", "JKO", "JKB", "JKC", "JKG", "JX", "JC"}


def _last_morph(eo: Eojeol) -> Optional[Morph]:
    return eo.morphs[-1] if eo.morphs else None


def _last_ec(eo: Eojeol) -> Optional[Morph]:
    for m in reversed(eo.morphs):
        if m.tag == "EC":
            return m
    return None


def _predicate_stem(lemma: str) -> str:
    """‘하다’→‘하’, ‘말하다’→‘말하’ 처럼 용언 어간 근사."""

    if lemma.endswith("다") and len(lemma) > 1:
        return lemma[:-1]
    return lemma


def _is_speech_related_verb(m: Morph) -> bool:
    """발화·사유 동사 후보 (lemma 가 ‘…하다’ 형태여도 매칭)."""

    base = _base_tag(m.tag)
    if base not in ("VV", "VX"):
        return False
    stem = _predicate_stem(m.lemma)
    return stem in _SPEECH_VERB_LEMMAS


def _is_indirect_quote_ec(m: Morph) -> bool:
    """간접 인용 연결어미 (`-ㄴ다고` 등). Kiwi lemma 변형 허용."""

    if m.tag != "EC":
        return False
    le = m.lemma
    if le in _INDIRECT_QUOTE_EC_LEMMAS:
        return True
    if le.endswith("다고") and ("ㄴ" in le or "ᆫ" in le or le.startswith("ㄴ")):
        return True
    return False


def _has_speech_verb_within(eojeols: list[Eojeol], start: int, max_steps: int = 4) -> bool:
    end = min(len(eojeols), start + max_steps)
    for j in range(start, end):
        for m in eojeols[j].morphs:
            if _is_speech_related_verb(m):
                return True
            # ‘말했다’: NNG 말 + XSV 하
            if _base_tag(m.tag) == "XSV" and m.lemma == "하":
                return True
    return False


def _is_dep_noun_with_case(eo: Eojeol) -> Optional[Morph]:
    """어절이 '것이/것을/줄로/바가' 같은 ‘의존명사+격(보)조사’ 구성이면 그 NNB 형태소 반환."""

    nnb = None
    for m in eo.morphs:
        if m.tag == "NNB" and m.lemma in _NOUN_CLAUSE_DEP_NOUNS:
            nnb = m
            break
    if not nnb:
        return None
    has_case = any(m.tag in _NOMINAL_CASE_TAGS for m in eo.morphs)
    if not has_case:
        return None
    return nnb


def _detect_trigger(
    eo: Eojeol, eojeols: list[Eojeol], i: int, is_last: bool
) -> Optional[dict]:
    """주어진 어절이 어떤 종류의 절을 ‘닫는’ 트리거를 가지고 있는지 판정.

    반환은 ``{"kind", "marker", "note"}`` 딕셔너리이거나 None.
    우선순위: 인용 > 명사(의존명사) > 명사(ETN) > 관형 > 부사/이어진.
    문장의 마지막 어절(주절 서술어)에 대해서는 트리거를 만들지 않는다.
    """

    if is_last:
        return None

    morphs = eo.morphs
    if not morphs:
        return None

    for m in morphs:
        if m.tag == "JKQ":
            return {"kind": "QUOT", "marker": m, "note": "직접 인용"}

    nnb = _is_dep_noun_with_case(eo)
    if nnb is not None and i > 0:
        prev_last = _last_morph(eojeols[i - 1])
        if prev_last is not None and prev_last.tag == "ETM":
            return {
                "kind": "NOUN",
                "marker": nnb,
                "note": f"의존명사 ‘{nnb.lemma}’ 결합",
            }

    etn = next((m for m in morphs if m.tag == "ETN"), None)
    if etn is not None:
        return {"kind": "NOUN", "marker": etn, "note": "명사형 전성어미"}

    last = morphs[-1]
    if last.tag == "ETM":
        if last.surface in _APPOSITIVE_ETM_FORMS or last.lemma in _APPOSITIVE_ETM_FORMS:
            note = "동격 관형절(인용+관형형)"
        else:
            note = "관계 관형절"
        return {"kind": "ADN", "marker": last, "note": note}

    ec = _last_ec(eo)
    if ec is not None:
        if ec.lemma in _ADV_EC_LEMMAS:
            return {"kind": "ADV", "marker": ec, "note": "부사형 전성어미"}
        if _is_indirect_quote_ec(ec):
            if _has_speech_verb_within(eojeols, i + 1):
                return {"kind": "QUOT", "marker": ec, "note": "간접 인용"}
            if ec.lemma == "고":
                return {"kind": "COORD", "marker": ec, "note": "대등하게 이어진 절"}
            # ‘-ㄴ다고/-라고/-자고/-(느)냐고’ 인데 발화 동사가 없는 드문 경우
            return {"kind": "QUOT", "marker": ec, "note": "간접 인용 (서술어 미상)"}
        if ec.lemma in _COORD_EC_LEMMAS:
            return {"kind": "COORD", "marker": ec, "note": "대등하게 이어진 절"}
        if ec.lemma in _SUBORD_EC_LEMMAS:
            return {"kind": "SUBORD", "marker": ec, "note": "종속적으로 이어진 절"}
        return {"kind": "SUBORD", "marker": ec, "note": "종속적으로 이어진 절"}

    return None


def _detect_predicate_clause(
    eojeols: list[Eojeol], main: Clause, children: list[Clause]
) -> Optional[Clause]:
    """서술절 식별: 한 절 안에 주격 표지 두 개, 두 번째 주어가 별도 서술어를 가짐.

    여기서는 이미 모든 안긴/이어진 자식 절이 분리된 뒤, MAIN 의 ‘잔여’ 어절
    범위에서만 검사한다.
    """

    n = len(eojeols)
    if n == 0:
        return None

    consumed: set[int] = set()
    for c in children:
        for k in range(c.span[0], c.span[1] + 1):
            consumed.add(k)
    remaining = [i for i in range(n) if i not in consumed]
    if len(remaining) < 3:
        return None

    def is_subject_eojeol(idx: int) -> bool:
        eo = eojeols[idx]
        if any(m.tag == "JKS" for m in eo.morphs):
            return True
        if any(m.tag == "JX" and m.lemma in {"은", "는"} for m in eo.morphs):
            return any(m.tag in ("NNG", "NNP", "NP", "NR", "NNB") for m in eo.morphs)
        return False

    subjects = [i for i in remaining if is_subject_eojeol(i)]
    if len(subjects) < 2:
        return None

    main_head = main.head_eojeol_index
    if main_head is None:
        return None
    second_subj = subjects[1]
    if second_subj >= main_head:
        return None

    pred_clause = Clause(
        kind="PRED",
        span=(second_subj, main_head),
        head_eojeol_index=main_head,
        marker_morph=None,
        note="이중 주어 구문",
    )
    return pred_clause


def detect_clauses(eojeols: list[Eojeol]) -> tuple[Clause, list[str]]:
    """절 트리(루트=MAIN)와 분석 중 발생한 경고 메시지 목록 반환."""

    notes: list[str] = []
    n = len(eojeols)
    if n == 0:
        return Clause(kind="MAIN", span=(0, -1)), notes

    main_head = n - 1
    last_eo = eojeols[-1]
    if not any(m.tag == "EF" for m in last_eo.morphs):
        notes.append("문장 마지막 어절에 종결어미(EF)가 없습니다. 분석 결과가 부정확할 수 있습니다.")

    main = Clause(
        kind="MAIN",
        span=(0, main_head),
        head_eojeol_index=main_head,
        marker_morph=last_eo.find_last("EF"),
    )

    flat: list[Clause] = []
    for i, eo in enumerate(eojeols):
        trigger = _detect_trigger(eo, eojeols, i, is_last=(i == n - 1))
        if trigger is None:
            continue
        flat.append(
            Clause(
                kind=trigger["kind"],
                span=(0, i),
                head_eojeol_index=i,
                marker_morph=trigger["marker"],
                note=trigger["note"],
            )
        )

    if flat:
        flat_sorted = sorted(flat, key=lambda c: c.head_eojeol_index or 0)
        for idx, cl in enumerate(flat_sorted):
            if idx + 1 < len(flat_sorted):
                outer = flat_sorted[idx + 1]
                outer.children.append(cl)
            else:
                main.children.append(cl)

    pred = _detect_predicate_clause(eojeols, main, flat)
    if pred is not None:
        already_pred = any(c.kind == "PRED" for c in main.children) or any(
            c.kind == "PRED" for c in flat
        )
        if not already_pred:
            main.children.append(pred)

    _refine_left_boundaries(main, eojeols)
    return main, notes


def _refine_left_boundaries(clause: Clause, eojeols: list[Eojeol]) -> None:
    """절 트리를 후위 순회하며 각 절의 좌경계를 좁힌다.

    규칙:
    - MAIN: ``span = (0, n-1)`` 그대로.
    - PRED: 이미 결정된 ``span`` 유지.
    - NOUN(의존명사 결합): 자식이 있으면 자식의 leftmost 와 같음.
    - QUOT(직접 인용): 부모의 left 부터 head 까지 범위에서 SSO 가 있는 어절을
      좌경계로 사용.
    - 그 외: ‘부모의 left 이상, head 미만’ 범위에서 자식 절 span 을 제외한 채
      head 쪽에서 가까운 JKS/JX(‘은/는/도/만/조차/마저/까지/부터’) 어절을 찾아
      그 위치를 좌경계로 한다. 후보가 없고 자식이 있으면 자식의 leftmost 를 사용.
    """

    parent_left = clause.span[0]

    for child in clause.children:
        _refine_left_boundaries(child, eojeols)

    if clause.kind == "MAIN" or clause.kind == "PRED":
        return

    head = clause.head_eojeol_index
    if head is None:
        return

    children_lefts = [c.span[0] for c in clause.children]
    children_rights = [c.span[1] for c in clause.children]
    children_min_left = min(children_lefts) if children_lefts else None

    new_left: int

    if clause.kind == "NOUN" and "의존명사" in clause.note and children_min_left is not None:
        new_left = children_min_left
    elif clause.kind == "QUOT" and "직접 인용" in clause.note:
        sso_at: int | None = None
        for i in range(parent_left, head):
            if any(m.tag == "SSO" for m in eojeols[i].morphs):
                sso_at = i
                break
        if sso_at is not None:
            new_left = sso_at
        elif children_min_left is not None:
            new_left = children_min_left
        else:
            new_left = parent_left
    else:
        descendant_ranges = _all_descendant_ranges(clause)

        def in_descendant(idx: int) -> bool:
            return any(a <= idx <= b for a, b in descendant_ranges)

        candidate: int | None = None
        for i in range(head - 1, parent_left - 1, -1):
            if in_descendant(i):
                continue
            eo = eojeols[i]
            if any(m.tag == "JKS" for m in eo.morphs):
                candidate = i
                break
            if any(
                m.tag == "JX"
                and m.lemma in {"은", "는", "도", "만", "조차", "마저", "까지", "부터"}
                for m in eo.morphs
            ):
                candidate = i
                break
        if candidate is not None:
            new_left = candidate
        elif children_min_left is not None:
            new_left = children_min_left
        else:
            new_left = parent_left

    new_left = max(parent_left, new_left)
    new_left = min(new_left, head)
    clause.span = (new_left, clause.span[1])


def _all_descendant_ranges(clause: Clause) -> list[tuple[int, int]]:
    """clause 의 모든 후손 절의 (left, right) 목록."""

    ranges: list[tuple[int, int]] = []
    for child in clause.children:
        ranges.append((child.span[0], child.span[1]))
        ranges.extend(_all_descendant_ranges(child))
    return ranges
