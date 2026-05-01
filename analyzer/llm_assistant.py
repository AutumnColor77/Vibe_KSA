"""Gemini 보조 분석 모듈.

규칙 기반 분석 결과(``Analysis``)를 입력으로 받아 Gemini 가 검토·부연하는
자연어 설명(마크다운)을 생성한다. ``GEMINI_API_KEY`` (또는
``GOOGLE_API_KEY``) 환경 변수가 없으면 자동으로 비활성화된다.

핵심 분석은 항상 규칙 기반으로 수행되며, LLM은 결과를 바꾸지 않고 ‘검토와
부연 설명’ 만 한다 (해석 가능성 우선).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from typing import Any, Optional

from .models import Analysis, COMPONENT_LABEL_KO, CLAUSE_LABEL_KO


_PROMPT = """다음은 학교 문법(중·고등학교 한국어) 기준으로 자동 분석된 문장이다. 너의 역할은 분석 결과를 검토하고 학습자에게 도움이 되도록 부연 설명하는 것이지, 분석 자체를 새로 생성하는 것이 아니다.

규칙:
1. ‘분석 결과 검토’와 ‘각 절·성분 설명’ 두 부분으로 한국어 마크다운을 작성한다.
2. 분석 결과가 학교 문법과 어긋나는 부분이 있으면 정중히 지적한다.
3. 안긴문장은 종류(명사절·관형절·부사절·서술절·인용절)와 그 근거(전성어미 등)를 풀어 설명한다.
4. 새로운 절을 임의로 만들거나, 결과 트리를 통째로 다시 그리지 않는다.
5. 200~400자 분량으로 간결하게.

[원문]
{text}

[규칙 기반 분석 결과 (요약)]
{summary}

[규칙 기반 분석 결과 (JSON)]
{payload}
"""


def _api_key() -> Optional[str]:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def is_available() -> bool:
    """Gemini 보조 사용 가능 여부."""

    if not _api_key():
        return False
    try:
        import google.generativeai  # noqa: F401
    except Exception:
        return False
    return True


def _summarize(analysis: Analysis) -> str:
    lines = [f"문장 종류: {analysis.sentence_type.label}"]
    for c in analysis.all_clauses():
        if c.kind == "MAIN":
            comps = ", ".join(
                f"{COMPONENT_LABEL_KO[comp.kind]}={analysis.eojeols[comp.eojeol_indices[0]].text}"
                for comp in c.components
            )
            lines.append(f"- 주절: {comps}")
        else:
            head = (
                analysis.eojeols[c.head_eojeol_index].text
                if c.head_eojeol_index is not None
                else ""
            )
            lines.append(
                f"- {CLAUSE_LABEL_KO[c.kind]}: 핵 ‘{head}’" + (f" — {c.note}" if c.note else "")
            )
    if analysis.notes:
        lines.append("주의: " + " / ".join(analysis.notes))
    return "\n".join(lines)


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return _to_jsonable(asdict(obj))
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    return obj


def explain(analysis: Analysis, model: str = "gemini-2.5-flash") -> str:
    """규칙 기반 결과에 대한 자연어 검토·부연 설명을 마크다운으로 반환.

    오류 시에는 원인을 사용자에게 보여주는 한국어 메시지를 반환한다.
    """

    api_key = _api_key()
    if not api_key:
        return "_Gemini API 키가 설정되어 있지 않습니다. `.env` 의 `GEMINI_API_KEY` 를 확인하세요._"

    try:
        import google.generativeai as genai
    except Exception as e:  # pragma: no cover
        return f"_`google-generativeai` 모듈을 불러올 수 없습니다: {e}_"

    try:
        genai.configure(api_key=api_key)
        gm = genai.GenerativeModel(model)
        payload = {
            "text": analysis.text,
            "sentence_type": analysis.sentence_type.label,
            "clauses": [
                {
                    "kind": c.kind,
                    "label": CLAUSE_LABEL_KO[c.kind],
                    "head": (
                        analysis.eojeols[c.head_eojeol_index].text
                        if c.head_eojeol_index is not None
                        and 0 <= c.head_eojeol_index < len(analysis.eojeols)
                        else None
                    ),
                    "note": c.note,
                    "components": [
                        {
                            "kind": comp.kind,
                            "label": COMPONENT_LABEL_KO[comp.kind],
                            "text": " ".join(
                                analysis.eojeols[i].text for i in comp.eojeol_indices
                            ),
                            "note": comp.note,
                        }
                        for comp in c.components
                    ],
                }
                for c in analysis.all_clauses()
            ],
            "notes": list(analysis.notes),
        }
        prompt = _PROMPT.format(
            text=analysis.text,
            summary=_summarize(analysis),
            payload=json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2),
        )
        resp = gm.generate_content(prompt)
        text = (getattr(resp, "text", None) or "").strip()
        if not text:
            return "_Gemini 가 빈 응답을 반환했습니다._"
        return text
    except Exception as e:
        return f"_Gemini 호출에 실패했습니다: {e}_"
