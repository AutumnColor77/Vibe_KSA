# 한국어 통사 자동 분석기

Streamlit 기반 웹 앱으로 한국어 문장의 통사 구조를 자동 분석합니다. 학교 문법 기준으로 다음을 식별·시각화합니다.

- **안긴문장** 종류: 명사절 / 관형절 / 부사절 / 서술절 / 인용절
- **이어진 문장** 종류: 대등 / 종속
- **문장 성분**: 주어 · 서술어 · 목적어 · 보어 · 관형어 · 부사어 · 독립어
- **문장 종류**: 홑문장 / 겹문장(안은문장 · 이어진 문장)

핵심 분석은 [Kiwi](https://github.com/bab2min/kiwipiepy) 형태소 분석기 위에 얹은 규칙 기반 엔진이며, `GEMINI_API_KEY`를 설정하면 Google Gemini가 자연어 보조 설명을 덧붙여 줍니다.

## 설치

Python 3.10 이상이 필요합니다. PowerShell 기준:

```powershell
cd f:\통사자동분석기
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Windows에서 `Activate.ps1` 실행이 막히면 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 후 다시 시도하세요.

## 환경 변수 (선택)

Gemini 보조 설명을 사용하려면 `.env` 파일을 만들고 키를 채웁니다.

```
GEMINI_API_KEY=발급받은_키
```

(`.env.example` 을 복사해 프로젝트 루트에 `.env` 로 두고 키를 넣으세요. 앱은 **`app.py`가 있는 폴더의 `.env`** 를 읽습니다. Streamlit 을 다시 시작해야 반영됩니다.)

## 실행

Windows에서 `pip install` 후 **`streamlit` 명령을 찾을 수 없다**고 나오면(사용자 `Scripts` 폴더가 PATH에 없을 때 흔함), 아래처럼 **모듈 실행**을 쓰세요.

```powershell
python -m streamlit run app.py
```

가상환경을 쓰고 `Activate.ps1`까지 했다면, 같은 폴더에서 보통 `streamlit run app.py` 도 동작합니다. 안 되면 항상 `python -m streamlit run app.py` 를 쓰면 됩니다.

브라우저가 열리면 사이드바에서 예문을 골라 「분석」 버튼을 누르거나, 텍스트박스에 직접 문장을 입력해 보세요.

## 테스트

```powershell
python -m pytest -q
```

(`pytest` 가 PATH 에 없으면 위와 같이 실행합니다.)

## 디렉터리 구조

```
analyzer/        # 분석 엔진 (형태소 → 절 → 성분 → 문장 종류)
  models.py
  tokenizer.py
  clause_detector.py
  component_analyzer.py
  sentence_classifier.py
  pipeline.py
  visualizer.py
  llm_assistant.py
examples/        # 사이드바 예문
tests/           # pytest 단위 테스트
app.py           # Streamlit UI
```

## 한계

- 규칙 기반은 형태소 표지에 의존합니다. 보조사 `은/는`이 주어와 주제를 모두 표시하거나, 같은 형태(`-고`)가 대등/종속/인용 어디로든 쓰일 수 있는 사례에서는 모호함이 남고 `Analysis.notes`에 경고가 기록됩니다.
- 구어체·신조어·장문 텍스트는 best-effort입니다.
- AI 보조는 규칙 기반 결과를 검토·부연하는 용도이며, 분석 결과 자체를 LLM이 만들지 않습니다(해석 가능성 우선).
