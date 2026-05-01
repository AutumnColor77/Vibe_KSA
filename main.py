"""Vercel 배포용 경량 ASGI 엔드포인트.

루트의 `app.py` 이름은 Vercel이 FastAPI/Flask 진입점으로 오인하므로 사용하지 않습니다.
전체 분석 UI는 Streamlit(`streamlit_app.py`)에서 실행합니다.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Vibe_KSA", version="0.1.0")


_REPO = "https://github.com/AutumnColor77/Vibe_KSA"


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Vibe_KSA · 통사 자동 분석기</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --card: #fff;
      --text: #0f172a;
      --muted: #64748b;
      --accent: #2563eb;
      --border: #e2e8f0;
    }}
    body {{
      font-family: "Pretendard Variable", Pretendard, system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      min-height: 100vh;
      line-height: 1.65;
    }}
    .wrap {{
      max-width: 36rem;
      margin: 0 auto;
      padding: 2.5rem 1.25rem 3rem;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.75rem 1.5rem;
      box-shadow: 0 1px 3px rgb(15 23 42 / 6%);
    }}
    h1 {{
      font-size: 1.5rem;
      font-weight: 700;
      margin: 0 0 0.35rem;
      letter-spacing: -0.02em;
    }}
    .sub {{
      color: var(--muted);
      font-size: 0.95rem;
      margin: 0 0 1.25rem;
    }}
    h2 {{
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
      margin: 1.35rem 0 0.5rem;
    }}
    h2:first-of-type {{ margin-top: 0; }}
    ul {{ margin: 0; padding-left: 1.15rem; }}
    li {{ margin: 0.45rem 0; }}
    code {{
      font-size: 0.88em;
      background: #f1f5f9;
      padding: 0.15em 0.4em;
      border-radius: 4px;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    footer {{
      margin-top: 1.5rem;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
      font-size: 0.875rem;
      color: var(--muted);
    }}
    .links {{ margin-top: 0.5rem; }}
    .links a {{ margin-right: 1rem; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Vibe_KSA</h1>
      <p class="sub">한국어 통사 자동 분석기</p>

      <p>문장의 통사 구조를 분석하는 <strong>웹 UI 전체</strong>는
        <strong>Streamlit</strong> 앱으로 제공됩니다. 이 주소(Vercel)에는 분석 화면 대신
        안내와 간단한 API만 있습니다.</p>

      <h2>로컬에서 실행</h2>
      <ul>
        <li><code>pip install -r requirements.txt</code></li>
        <li><code>streamlit run streamlit_app.py</code></li>
      </ul>

      <h2>웹에 공개(무료)</h2>
      <ul>
        <li><a href="https://share.streamlit.io/">Streamlit Community Cloud</a>에서 GitHub 저장소를 연결</li>
        <li>Main file을 <code>streamlit_app.py</code>로 지정</li>
      </ul>

      <footer>
        소스: <a href="{_REPO}">{_REPO}</a>
        <div class="links">
          <a href="/docs">OpenAPI 문서</a>
          <a href="/health">헬스 확인</a>
        </div>
      </footer>
    </div>
  </div>
</body>
</html>"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
