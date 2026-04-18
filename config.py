"""
봇 설정 및 상수 정의
"""
import os
import logging
import discord
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# =========================================================
# Discord 토큰 및 기본 설정
# =========================================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("❌ DISCORD_TOKEN 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

# 관리자 사용자 ID
ALLOWED_USER_IDS = list(map(
    int,
    filter(None, os.getenv("ALLOWED_USER_IDS", "").split(","))
))

# =========================================================
# 경로 설정
# =========================================================
BASE_DIR = Path(__file__).parent
SETTINGS_FILE = BASE_DIR / "settings.json"

# =========================================================
# Rate Limiting (속도 제한)
# =========================================================
CHANNEL_OPERATION_DELAY = 0.5  # 채널 작업 대기 시간 (초)
RENAME_OPERATION_DELAY = 1.0   # 이름 변경 작업 대기 시간 (초)
MESSAGE_HISTORY_LIMIT = 10     # 메시지 히스토리 조회 수

# =========================================================
# Embed 색상
# =========================================================
EMBED_SUCCESS_COLOR = discord.Color.green()
EMBED_ERROR_COLOR = discord.Color.red()
EMBED_INFO_COLOR = discord.Color.blue()
EMBED_WARNING_COLOR = discord.Color.orange()

# =========================================================
# 에러 메시지
# =========================================================
MSG_UNAUTHORIZED = "❌ 권한이 없습니다."
MSG_NOT_FOUND = "⚠️ 찾을 수 없습니다."
MSG_SUCCESS = "✅ 완료!"

# =========================================================
# 로깅 설정
# =========================================================
log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
log_level = logging.INFO

# 파일 로거
file_handler = logging.FileHandler(
    BASE_DIR / 'bot.log',
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(log_format))

# 콘솔 로거
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(log_format))

# 기본 로깅 설정
logging.basicConfig(
    level=log_level,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)
