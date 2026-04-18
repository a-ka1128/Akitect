"""
Discord 봇 메인 파일

봇 초기화, 이벤트 핸들러, Cog 로드 등을 담당합니다.
"""
import logging
from pathlib import Path

import discord
from discord.ext import commands

import config
from utils import SettingsManager, CategoryManager, admin_only

logger = logging.getLogger(__name__)

# =========================================================
# 봇 초기화
# =========================================================
intents = discord.Intents.default()
intents.members = True          # 멤버 관련 이벤트
intents.message_content = True  # 메시지 내용 접근

bot = commands.Bot(command_prefix='!', intents=intents)

# =========================================================
# 이벤트
# =========================================================


@bot.event
async def on_ready():
    """봇 준비 완료 이벤트"""
    logger.info("=" * 60)
    logger.info(f"✅ 로그인 성공: {bot.user}")
    logger.info(f"📌 설정 파일: {config.SETTINGS_FILE}")
    logger.info("=" * 60)

    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ 슬래시 명령어 동기화: {len(synced)}개")
    except Exception as e:
        logger.error(f"❌ 슬래시 명령어 동기화 실패: {e}", exc_info=True)


@bot.event
async def on_member_join(member: discord.Member):
    """
    멤버 입장 이벤트

    자동 역할 부여 및 방 생성
    """
    logger.info(f"👤 멤버 입장: {member.name} ({member.id})")

    try:
        settings = SettingsManager()
        guild_id = str(member.guild.id)

        # 자동 역할 부여
        auto_role_id = settings.get_auto_role(guild_id)
        if auto_role_id:
            role = member.guild.get_role(auto_role_id)
            if role:
                try:
                    await member.add_roles(role)
                    logger.info(f"✅ 역할 부여: {member.name} → {role.name}")
                except discord.Forbidden:
                    logger.error(f"❌ 권한 부족: {role.name}을 부여할 수 없습니다")
                except Exception as e:
                    logger.error(f"❌ 역할 부여 오류: {e}")

        # 방 생성
        await create_user_room(member.guild, member)

    except Exception as e:
        logger.error(f"❌ 멤버 입장 처리 오류: {e}", exc_info=True)


# =========================================================
# 방 생성 함수
# =========================================================


async def create_user_room(guild: discord.Guild, member: discord.Member) -> tuple[bool, str]:
    """
    사용자 방 생성

    기존 카테고리가 있으면 멤버 추가, 없으면 새로 생성

    Args:
        guild: Discord Guild
        member: 멤버

    Returns:
        (성공 여부, 메시지)
    """
    try:
        settings = SettingsManager()
        guild_id = str(guild.id)

        # 템플릿 확인
        channels = settings.get_channels(guild_id)
        if not channels:
            logger.warning(f"⚠️ 템플릿이 없습니다: {guild.name}")
            return False, "설정된 채널 템플릿이 없습니다."

        # 카테고리 찾기
        category_manager = CategoryManager(guild)
        category = category_manager.find_category_by_name(member.display_name)

        if category:
            # 기존 카테고리에 추가
            success = await category_manager.add_member_to_category(category, member)
            if success:
                logger.info(f"✅ 멤버 추가: {member.name} → {category.name}")
                return True, f"'{category.name}' 그룹에 추가되었습니다."
            else:
                return False, "권한을 설정할 수 없습니다."

        # 새로운 카테고리 생성
        logger.info(f"새로운 카테고리 생성 시작: {member.display_name}")

        new_category = await category_manager.create_category(
            member.display_name,
            member
        )

        if not new_category:
            return False, "카테고리 생성에 실패했습니다."

        # 여기서는 채널 생성을 하지 않음 (방 생성 명령어에서 처리)
        logger.info(f"✅ 카테고리 생성: {new_category.name}")
        return True, f"새로운 카테고리 '{new_category.name}'가 생성되었습니다."

    except Exception as e:
        logger.error(f"❌ 방 생성 오류: {e}", exc_info=True)
        return False, f"오류가 발생했습니다: {str(e)}"


# =========================================================
# Cog 로드
# =========================================================


async def load_cogs():
    """
    cogs 디렉토리에서 모든 Cog 로드

    각 Cog 파일은 setup() 함수를 포함해야 합니다.
    """
    cogs_dir = Path(__file__).parent / "cogs"

    if not cogs_dir.exists():
        logger.warning("⚠️ cogs 디렉토리가 없습니다")
        return

    # Cog 파일 로드
    for cog_file in sorted(cogs_dir.glob("*.py")):
        if cog_file.name.startswith("_"):
            continue

        cog_name = cog_file.stem
        try:
            await bot.load_extension(f"cogs.{cog_name}")
            logger.info(f"✅ Cog 로드: {cog_name}")
        except Exception as e:
            logger.error(f"❌ Cog 로드 실패 ({cog_name}): {e}", exc_info=True)


@bot.event
async def setup_hook():
    """봇 시작 전 초기화"""
    await load_cogs()


# =========================================================
# 실행
# =========================================================


def main():
    """봇 실행"""
    logger.info("🚀 봇 시작 중...")
    try:
        bot.run(config.DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"❌ 봇 실행 오류: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
