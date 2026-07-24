# SafeON 거리 관제

두 노트북 웹캠 기반 측정 프로그램이 관제 노트북으로 아래 두 값만 보내는
구조입니다.

```json
{
  "distance_m": 0.82,
  "distance_level": "DANGER"
}
```

통신은 브로커가 필요 없는 일반 HTTP POST 한 번으로 끝납니다. 관제 서버는
수신시각, 근로자·장비 ID, 온습도, 배터리, 장치 상태, 위험성 평가,
개선권고와 리포트 정보를 목업값으로 채웁니다. 기존 대시보드 UI와
사건 ID 클릭형 개별 리포트는 유지됩니다.

## 1. 관제 노트북 실행

PowerShell에서 프로젝트 폴더로 이동한 뒤 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

같은 노트북에서 `http://127.0.0.1:8000`을 열면 됩니다. 다른 노트북에서
보려면 관제 노트북에서 `ipconfig`로 IPv4 주소를 확인하고
`http://관제노트북IP:8000`을 엽니다. Windows 방화벽 창이 뜨면 현재
사용 중인 사설 네트워크에서 Python의 접근을 허용합니다.

## 2. 거리값 한 건 보내기

관제 노트북 자체에서 확인:

```powershell
.\.venv\Scripts\python.exe distance_sender.py 0.82 DANGER
```

측정 노트북에서 관제 노트북으로 전송:

```powershell
.\.venv\Scripts\python.exe distance_sender.py 0.82 DANGER --server http://192.168.0.10:8000
```

웹캠 거리 측정 코드에는 아래 두 줄만 연결하면 됩니다.

```python
from distance_sender import send_distance

send_distance(distance_m, distance_level, server="http://192.168.0.10:8000")
```

`distance_level`은 `SAFE`, `CAUTION`, `DANGER` 중 하나입니다. 서버는
추가 필드가 포함된 요청을 거절하므로 실제 송신 계약은 언제나 두
필드로 유지됩니다.

직접 HTTP를 호출하려면:

```text
POST http://관제노트북IP:8000/api/distance
Content-Type: application/json

{"distance_m":0.82,"distance_level":"DANGER"}
```

## 3. 30초 시연

서버를 실행한 상태에서 별도 PowerShell을 열어:

```powershell
.\.venv\Scripts\python.exe simulator.py
```

다른 관제 노트북으로 보내려면:

```powershell
.\.venv\Scripts\python.exe simulator.py --server http://192.168.0.10:8000
```

30초 동안 `SAFE → CAUTION → DANGER → CAUTION → SAFE`가 자연스럽게
표시되고, 위험 진입 시 사건이 생성됩니다. 완료 후 대시보드의 사건 ID를
누르면 최소 접근거리, 시작·종료시각, 단계, 목업 온습도와 조치 상태가
포함된 개별 리포트를 확인할 수 있습니다.

## ESP32를 반드시 송신기로 쓸 때

가장 단순하고 장애 지점이 적은 경로는 웹캠 측정 노트북이
`distance_sender.py`로 직접 전송하는 것입니다. ESP32가 반드시 Wi-Fi
송신을 담당해야 하면 `esp32_http_sender.ino`의 Wi-Fi 정보와 관제
노트북 IP만 바꾼 뒤 `sendDistance(distance, level)`을 호출합니다.

## 확인용 API

- `GET /api/health`: 서버 상태와 정확한 입력 필드
- `POST /api/distance`: 거리값·거리단계 수신
- `GET /api/live`: 대시보드 최신값
- `GET /api/incidents`: 사건 목록
- `GET /api/incidents/{event_id}`: 개별사건 리포트
- `GET /docs`: FastAPI 자동 API 문서
