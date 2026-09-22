# Akitect

새 멤버가 들어오면 그 사람 전용 카테고리·채널을 자동으로 만들어 주는 디스코드 봇.
비어 있는 방은 자동 청소한다 (음성 채널에 접속자가 있으면 건너뜀).

**상태 (2026-09-22): 운영 중 · 유지보수 모드.** GCP VM(`aka-pvm`)의 systemd 유닛
`discord-bot` 으로 24시간 돌고 있다. 예정된 기능 추가는 없고, 문제가 생길 때만 손댄다.
켜고 끄는 건 `Claude/Akadeck` 대시보드에서.

## 실행 (로컬)

```bash
py -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt
./venv/Scripts/python.exe main.py
```

`.env` 에 봇 토큰, `settings.json` 에 정적 설정. VM 배포는 `deploy.sh`.
