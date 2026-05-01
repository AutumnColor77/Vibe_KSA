"""분석 결과를 표현하는 데이터 모델.

분석 파이프라인 단계 사이에 흘러다니는 모든 객체는 여기 정의된
dataclass로만 표현된다. UI/시각화/LLM 모듈은 이 객체들에만 의존한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator, Literal, Optional


ClauseKind = Literal[
    "MAIN",     # 전체 문장의 주절
    "NOUN",     # 명사절
    "ADN",      # 관형절
    "ADV",      # 부사절
    "PRED",     # 서술절
    "QUOT",     # 인용절
    "COORD",    # 대등하게 이어진 절
    "SUBORD",   # 종속적으로 이어진 절
]

ComponentKind = Literal[
    "SUBJ",     # 주어
    "PRED",     # 서술어
    "OBJ",      # 목적어
    "COMPL",    # 보어
    "ADN",      # 관형어
    "ADV",      # 부사어
    "INDEP",    # 독립어
]

CLAUSE_LABEL_KO: dict[str, str] = {
    "MAIN": "주절",
    "NOUN": "명사절",
    "ADN": "관형절",
    "ADV": "부사절",
    "PRED": "서술절",
    "QUOT": "인용절",
    "COORD": "대등하게 이어진 절",
    "SUBORD": "종속적으로 이어진 절",
}

COMPONENT_LABEL_KO: dict[str, str] = {
    "SUBJ": "주어",
    "PRED": "서술어",
    "OBJ": "목적어",
    "COMPL": "보어",
    "ADN": "관형어",
    "ADV": "부사어",
    "INDEP": "독립어",
}

COMPONENT_COLOR: dict[str, str] = {
    "SUBJ": "#1d4ed8",
    "PRED": "#b91c1c",
    "OBJ": "#047857",
    "COMPL": "#7c3aed",
    "ADN": "#c2410c",
    "ADV": "#0e7490",
    "INDEP": "#6b7280",
}

CLAUSE_COLOR: dict[str, str] = {
    "MAIN": "#0f172a",
    "NOUN": "#1d4ed8",
    "ADN": "#c2410c",
    "ADV": "#0e7490",
    "PRED": "#b91c1c",
    "QUOT": "#7c3aed",
    "COORD": "#15803d",
    "SUBORD": "#a16207",
}


@dataclass(frozen=True)
class Morph:
    """Kiwi 토큰 하나에 대응."""

    surface: str
    lemma: str
    tag: str
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass
class Eojeol:
    """공백 단위 어절. 한 어절은 하나 이상의 형태소로 구성된다."""

    index: int
    text: str
    morphs: list[Morph] = field(default_factory=list)
    start: int = 0
    end: int = 0

    def has_tag(self, *tags: str) -> bool:
        return any(m.tag in tags for m in self.morphs)

    def has_lemma_tag(self, lemma: str, tag: str) -> bool:
        return any(m.lemma == lemma and m.tag == tag for m in self.morphs)

    def last_tag(self) -> Optional[str]:
        return self.morphs[-1].tag if self.morphs else None

    def find(self, *tags: str) -> Optional[Morph]:
        for m in self.morphs:
            if m.tag in tags:
                return m
        return None

    def find_last(self, *tags: str) -> Optional[Morph]:
        for m in reversed(self.morphs):
            if m.tag in tags:
                return m
        return None


@dataclass
class Component:
    """절 안의 문장 성분."""

    kind: ComponentKind
    eojeol_indices: list[int]
    note: str = ""

    @property
    def label_ko(self) -> str:
        return COMPONENT_LABEL_KO[self.kind]


@dataclass
class Clause:
    """절 트리의 노드.

    - ``kind`` : 절의 종류
    - ``span`` : 이 절을 구성하는 어절 인덱스의 (시작, 끝) (끝 포함)
    - ``head_eojeol_index`` : 절을 결정짓는 핵심 어절 (전성어미·연결어미·서술어 등)
    - ``marker_morph`` : 절을 식별한 표지 형태소 (있으면)
    - ``children`` : 안긴/이어진 자식 절 목록
    - ``components`` : 이 절 자체의 직속 문장 성분
    - ``role`` : 모절에서 이 절이 담당하는 역할 (주어/목적어/관형어 등). 선택.
    - ``note`` : 부연 설명 (관계 관형절·동격 관형절 구분 등)
    """

    kind: ClauseKind
    span: tuple[int, int]
    head_eojeol_index: Optional[int] = None
    marker_morph: Optional[Morph] = None
    children: list["Clause"] = field(default_factory=list)
    components: list[Component] = field(default_factory=list)
    role: Optional[ComponentKind] = None
    note: str = ""

    @property
    def label_ko(self) -> str:
        return CLAUSE_LABEL_KO[self.kind]

    def iter(self) -> Iterator["Clause"]:
        yield self
        for child in self.children:
            yield from child.iter()


@dataclass
class SentenceType:
    """문장 종류 요약.

    - ``simple`` : True면 홑문장
    - ``has_embedded`` : 안긴문장(명사·관형·부사·서술·인용절)을 가지고 있는가
    - ``has_conjoined`` : 이어진 문장(대등/종속)인가
    - ``embedded_kinds`` : 포함된 안긴문장 종류 (중복 제거)
    - ``conjoined_kind`` : 'COORD' / 'SUBORD' / None
    - ``label`` : 사람이 읽을 한 줄 요약
    """

    simple: bool
    has_embedded: bool
    has_conjoined: bool
    embedded_kinds: list[ClauseKind]
    conjoined_kind: Optional[ClauseKind]
    label: str


@dataclass
class Analysis:
    """``analyze(text)`` 가 반환하는 최상위 결과."""

    text: str
    eojeols: list[Eojeol]
    root: Clause
    sentence_type: SentenceType
    notes: list[str] = field(default_factory=list)

    def all_clauses(self) -> Iterable[Clause]:
        return list(self.root.iter())

    def embedded_clauses(self) -> list[Clause]:
        return [
            c
            for c in self.all_clauses()
            if c.kind in {"NOUN", "ADN", "ADV", "PRED", "QUOT"}
        ]

    def conjoined_clauses(self) -> list[Clause]:
        return [c for c in self.all_clauses() if c.kind in {"COORD", "SUBORD"}]
