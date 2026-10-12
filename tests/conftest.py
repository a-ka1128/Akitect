"""테스트 공통 설정 — config 가 토큰을 요구하므로 가짜 값을 넣는다"""
import os
import sys
from pathlib import Path

os.environ.setdefault("DISCORD_TOKEN", "test-token")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
