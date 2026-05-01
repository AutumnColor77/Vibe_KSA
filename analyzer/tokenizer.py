"""Kiwi 형태소 분석기를 어절(eojeol) 단위로 묶어주는 래퍼."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING

from .models import Eojeol, Morph

if TYPE_CHECKING:
    from kiwipiepy import Kiwi


@lru_cache(maxsize=1)
def _get_kiwi() -> "Kiwi":
    """싱글턴으로 Kiwi 인스턴스를 반환. 첫 호출에서만 모델을 로드한다."""

    from kiwipiepy import Kiwi  # 무거운 import 는 lazy 로

    return Kiwi()


_WS_RE = re.compile(r"\s+")


def _eojeol_spans(text: str) -> list[tuple[int, int, str]]:
    """원문에서 (start, end, surface) 어절 스팬 목록 반환."""

    spans: list[tuple[int, int, str]] = []
    pos = 0
    for match in re.finditer(r"\S+", text):
        start, end = match.start(), match.end()
        spans.append((start, end, text[start:end]))
        pos = end
    _ = pos  # silence linter
    return spans


def _to_morph(token) -> Morph:
    """kiwipiepy Token을 우리 ``Morph`` 로 변환."""

    surface = getattr(token, "form", None) or token[0]
    tag = getattr(token, "tag", None) or token[1]
    start = getattr(token, "start", None)
    if start is None:
        start = token[2]
    length = getattr(token, "len", None)
    if length is None:
        length = token[3]
    lemma = getattr(token, "lemma", None) or surface
    return Morph(
        surface=surface,
        lemma=lemma,
        tag=tag,
        start=start,
        end=start + length,
    )


def tokenize(text: str) -> list[Eojeol]:
    """문장을 어절 리스트로 변환.

    각 어절은 그 어절의 문자 범위 안에 시작 지점이 들어가는 형태소들을
    가진다. 어절이 비어 있는 경우(분석 실패)는 해당 어절의 표면형만으로
    placeholder 형태소를 생성한다.
    """

    if not text or not text.strip():
        return []

    spans = _eojeol_spans(text)
    if not spans:
        return []

    kiwi = _get_kiwi()
    raw_tokens = kiwi.tokenize(text)
    morphs = [_to_morph(t) for t in raw_tokens]

    eojeols: list[Eojeol] = []
    for index, (start, end, surface) in enumerate(spans):
        bucket = [m for m in morphs if start <= m.start < end]
        if not bucket:
            bucket = [
                Morph(surface=surface, lemma=surface, tag="UNK", start=start, end=end)
            ]
        eojeols.append(
            Eojeol(
                index=index,
                text=surface,
                morphs=bucket,
                start=start,
                end=end,
            )
        )

    return eojeols


def split_sentences(text: str) -> list[str]:
    """Kiwi 의 문장 분리를 사용. 실패 시 단일 문장으로 반환."""

    text = text.strip()
    if not text:
        return []
    kiwi = _get_kiwi()
    try:
        sents = kiwi.split_into_sents(text)
    except Exception:
        return [text]
    if not sents:
        return [text]
    return [s.text if hasattr(s, "text") else str(s) for s in sents]
