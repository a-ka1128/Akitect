"""
봇 설정 및 상수 정의
"""
import os
import logging
from logging.handlers import RotatingFileHandler
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

# 봇을 쓸 수 있는 서버 ID (비워두면 제한 없음)
# 설정하면 목록에 없는 서버에서는 명령어·입장/퇴장 처리를 하지 않는다.
ALLOWED_GUILD_IDS = set(map(
    int,
    filter(None, os.getenv("ALLOWED_GUILD_IDS", "").split(","))
))

# =========================================================
# 경로 설정
# =========================================================
BASE_DIR = Path(__file__).parent
SETTINGS_FILE = BASE_DIR / "settings.json"
TEMPLATE_FILES_DIR = BASE_DIR / "template_files"  # 템플릿 첨부 파일 저장 디렉토리
ARCHIVE_DIR = BASE_DIR / "archives"  # 방 보관본이 커서 채널에 못 올릴 때 저장하는 디렉토리

# =========================================================
# Rate Limiting (속도 제한)
# =========================================================
# discord.py가 레이트리밋(429)을 자동으로 처리하므로 과도한 대기는 불필요하다.
# 약간의 버퍼만 두어 연속 작업 속도를 높인다.
CHANNEL_OPERATION_DELAY = 0.5  # 채널 작업 간 대기 시간 (초)
RENAME_OPERATION_DELAY = 0.5   # 이름 변경 작업 간 대기 시간 (초)
MESSAGE_HISTORY_LIMIT = 10     # 메시지 히스토리 조회 수

# =========================================================
# 용량·남용 제한
# =========================================================
GUILD_CHANNEL_LIMIT = 500                           # 디스코드 서버당 채널(카테고리 포함) 최대 수
TEMPLATE_FILES_MAX_TOTAL_BYTES = 200 * 1024 * 1024  # 서버당 템플릿 첨부 파일 총량
ARCHIVE_MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024     # 보관본에 담을 첨부 1개 최대 크기
ARCHIVE_MAX_TOTAL_BYTES = 200 * 1024 * 1024         # 보관본 1개에 담을 첨부 총량
HELP_COOLDOWN_SECONDS = 300                         # /도움 재사용 대기 시간 (사용자별)

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

# 파일 로거 (5MB × 3개로 순환 — 디스크가 로그로 차지 않도록)
file_handler = RotatingFileHandler(
    BASE_DIR / 'bot.log',
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
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
