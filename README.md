# GenAI Pseudonymizer

이 프로젝트는 **브라우저 확장 프로그램**과 **로컬 Python 서버(app.py)**로 구성되어 있습니다.  
확장 프로그램은 프롬프트를 가명화하여 전송하고, 서버는 이를 처리합니다.

---

## 1. 폴더 구조

```python
.
├── browser-extension/ # Chrome Extension 코드
├── pseudonymization/ # 가명화 관련 Python 모듈
├── utils/ # 유틸리티 코드
├── app.py # 로컬 서버 실행 엔트리포인트
├── pseudo-log.json # 프롬프트 로그
├── requirements.txt # Python dependencies
├── README.md # 사용법 설명
```

## 2. Installation and Execute

### 2.1 저장소 클론

```bash
git clone https://github.com/Future-Challenge/prompt-psuedonymization-server.git
```

### 2.2 환경 설정
Windows(powershell)
```script
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
### 2.3 서버 실행
```bash
python app.py
```
- 서버가 실행되면 http://127.0.0.1:5000 에서 요청을 처리한다.

### 2.4 브라우저 확장 프로그램 설치
  1. 크롬 브라우저에서 chrome://extensions/ 접속
  2. 우측 상단 토글 → 개발자 모드 활성화
  3. 압축 해제된 확장 프로그램 로드 클릭
  4. browser-extension 폴더 선택

## 2. How to use
- 확장 프로그램을 설치한 상태에서 ChatGPT/Anthropic API 웹 콘솔에서 Prompt를 보내면 요청이 가명화됩니다.**(단, 최초 실행의 경우 NER 모델이 설치되기 전이므로 가명화가 실행되지 않고 NER 모델이 설치됩니다.)**

- app.py 서버를 실행 중이어야 정상 동작합니다.

- 변환된 프롬프트와 원본은 pseudo-log.json에 로깅되어 Debugging에 사용 가능

---