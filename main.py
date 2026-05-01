"""Vercel 배포용 경량 ASGI 엔드포인트.

루트의 `app.py` 이름은 Vercel이 FastAPI/Flask 진입점으로 오인하므로 사용하지 않습니다.
전체 분석 UI는 Streamlit(`streamlit_app.py`)에서 실행합니다.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Vibe_KSA", version="0.1.0")


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Vibe_KSA</title>
</head>
<body style="font-family:system-ui,sans-serif;max-width:42rem;margin:2rem auto;line-height:1.6;">
  <h1>Vibe_KSA</h1>
  <p>한국어 통사 자동 분석기의 <strong>전체 웹 UI는 Streamlit</strong>으로 제공됩니다.</p>
  <ul>
    <li>로컬: <code>pip install -r requirements.txt</code> 후
      <code>streamlit run streamlit_app.py</code></li>
    <li>무료 호스팅: <a href="https://share.streamlit.io/">Streamlit Community Cloud</a>에
      이 저장소를 연결하고 Main file을 <code>streamlit_app.py</code>로 지정하세요.</li>
  </ul>
  <p>이 주소는 Vercel에 올린 안내·API용 페이지입니다.
    <a href="/docs">OpenAPI 문서</a></p>
</body>
</html>"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
