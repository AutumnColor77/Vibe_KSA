"""``analyze`` 통합 테스트 — 플랜 §8 표준 예문."""

from __future__ import annotations

import pytest

from analyzer import analyze


def _kinds(analysis):
    return sorted({c.kind for c in analysis.root.iter()})


def test_noun_clause_um():
    a = analyze("그가 범인임이 밝혀졌다.")
    assert "NOUN" in _kinds(a)
    assert not a.sentence_type.simple


def test_noun_clause_gi():
    a = analyze("나는 그가 떠나기를 바랐다.")
    assert "NOUN" in _kinds(a)


def test_noun_clause_neun_geot():
    a = analyze("비가 오는 것이 보인다.")
    kinds = _kinds(a)
    assert "NOUN" in kinds
    assert "ADN" in kinds


def test_adn_relative():
    a = analyze("내가 어제 만난 사람은 친절하다.")
    assert "ADN" in _kinds(a)
    preds = [c for c in a.root.components if c.kind == "PRED"]
    assert preds, "주절 서술어(형용사파생 XSA) 인식"


def test_adn_appositive():
    a = analyze("그가 떠났다는 사실은 슬프다.")
    adns = [c for c in a.all_clauses() if c.kind == "ADN"]
    assert adns
    assert any("동격" in (c.note or "") for c in adns)


@pytest.mark.skip(reason="Kiwi 가 ‘없이’를 MAG 한 덩어리로 잡아 EC 트리거가 없음")
def test_adv_clause_i():
    a = analyze("비가 소리도 없이 내린다.")
    assert "ADV" in _kinds(a)


def test_adv_clause_ge():
    a = analyze("꽃이 아름답게 피었다.")
    assert "ADV" in _kinds(a)


def test_predicate_clause_double_subject():
    a = analyze("코끼리는 코가 길다.")
    assert "PRED" in _kinds(a)


def test_quot_direct():
    a = analyze('그는 "내일 가겠다"라고 말했다.')
    assert "QUOT" in _kinds(a)


def test_quot_indirect():
    a = analyze("그가 온다고 했다.")
    kinds = _kinds(a)
    assert "QUOT" in kinds
    assert "SUBORD" not in kinds


def test_coord():
    a = analyze("비가 오고 바람이 분다.")
    assert "COORD" in _kinds(a)


def test_subord():
    a = analyze("비가 와서 길이 미끄럽다.")
    assert "SUBORD" in _kinds(a)


def test_simple_sentence():
    a = analyze("영희가 책을 읽는다.")
    assert a.sentence_type.simple


def test_visualizer_dot_smoke():
    from analyzer.visualizer import clause_tree_dot

    a = analyze("비가 오는 것이 보인다.")
    dot = clause_tree_dot(a)
    assert "digraph" in dot
    assert "명사절" in dot
