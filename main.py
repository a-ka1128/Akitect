"""
Discord 봇 메인 파일

봇 초기화, 이벤트 핸들러, Cog 로드 등을 담당합니다.
"""
import logging
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

import config
from utils import SettingsManager, CategoryManager, Archiver, build_member_room

logger = logging.getLogger(__name__)


def guild_allowed(guild: discord.Guild | None) -> bool:
    """ALLOWED_GUILD_IDS 가 설정돼 있으면 그 서버에서만 동작"""
    if guild is None:
        return False
    return not config.ALLOWED_GUILD_IDS or guild.id in config.ALLOWED_GUILD_IDS


class GuardedTree(app_commands.CommandTree):
    """허용 서버 확인 + 명령어 오류 공통 처리"""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if guild_allowed(interaction.guild):
            return True
        # 자동완성 요청에는 메시지로 응답할 수 없다 (조용히 거부)
        if interaction.type is discord.InteractionType.application_command:
            await interaction.response.send_message(
                "❌ 이 서버에서는 사용할 수 없는 봇입니다.", ephemeral=True
            )
        return False

    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏳ 잠시 후 다시 시도하세요. ({error.retry_after:.0f}초 남음)"
        elif isinstance(error, app_commands.CheckFailure):
            # admin_only 등이 이미 안내 메시지를 보냈으면 조용히 끝낸다
            if interaction.response.is_done():
                return
            msg = config.MSG_UNAUTHORIZED
        else:
            command = interaction.command.name if interaction.command else "?"
            logger.error(f"❌ 명령어 오류 (/{command}): {error}", exc_info=error)
            msg = "❌ 명령 처리 중 오류가 발생했습니다."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass


# =========================================================
# 봇 초기화
# =========================================================
intents = discord.Intents.default()
intents.members = True  # 멤버 입장/퇴장 감지에 필요 (privileged intent)
intents.message_content = True  # 방 보관 시 과거 메시지 내용을 읽으려면 필요 (privileged intent)

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    tree_cls=GuardedTree,
    # 슬래시 명령어는 서버에서만 (DM 에서는 목록에 안 뜸)
    allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=False, private_channel=False),
    # @everyone/@here 와 역할 멘션은 기본 차단 (/도움 처럼 필요한 곳에서만 명시적으로 허용)
    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False),
)

# ✅ 전역 SettingsManager 인스턴스 (모든 곳에서 공유)
# 실행 위치(CWD)와 상관없이 항상 프로젝트 폴더의 settings.json 을 쓴다
settings_manager = SettingsManager(config.SETTINGS_FILE)

# =========================================================
# 이벤트
# =========================================================


@bot.event
async def on_ready():
    """봇 준비 완료 이벤트"""
    logger.info("=" * 60)
    logger.info(f"✅ 로그인 성공: {bot.user}")
    logger.info(f"📌 설정 파일: {config.SETTINGS_FILE}")
    for guild in bot.guilds:
        if not guild_allowed(guild):
            logger.warning(f"⚠️ 허용되지 않은 서버에 들어가 있음 (무시함): {guild.name} ({guild.id})")
    logger.info("=" * 60)
    # 슬래시 명령어 sync는 setup_hook에서 1회만 수행한다.
    # on_ready는 재접속(RESUME)마다 호출되므로 여기서 sync하면 매번 중복 sync된다.


@bot.event
async def on_guild_join(guild: discord.Guild):
    """새 서버 초대 — 허용 목록 밖이면 경고만 남긴다 (실수로 본 서버를 나가지 않도록 자동 퇴장은 안 함)"""
    if not guild_allowed(guild):
        logger.warning(f"⚠️ 허용되지 않은 서버에 초대됨 (무시함): {guild.name} ({guild.id})")


@bot.event
async def on_member_join(member: discord.Member):
    """
    멤버 입장 이벤트

    가입 심사(멤버십 스크리닝)를 쓰는 서버는 심사를 통과한 뒤(on_member_update)에 처리한다.
    → 규칙 동의도 안 한 계정이 몰려 들어와 방을 대량으로 만드는 것을 막는다.
    """
    if member.bot or not guild_allowed(member.guild):
        return

    logger.info(f"👤 멤버 입장: {member.name} ({member.id})")

    if member.pending:
        logger.info(f"⏳ 가입 심사 대기 — 통과 후 방 생성: {member.name}")
        return

    await handle_new_member(member)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    """가입 심사 통과 시 입장 처리"""
    if after.bot or not guild_allowed(after.guild):
        return
    if before.pending and not after.pending:
        logger.info(f"✅ 가입 심사 통과: {after.name} ({after.id})")
        await handle_new_member(after)


async def handle_new_member(member: discord.Member):
    """자동 역할 부여 및 방 생성"""
    try:
        guild_id = str(member.guild.id)

        # 자동 역할 부여
        auto_role_id = settings_manager.get_auto_role(guild_id)
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

        # 예전에 만든 본인 방이 남아 있으면 (보관 실패로 삭제되지 않은 경우 등) 다시 열어준다.
        # 소유자 ID 기록 또는 '본인 ID 권한'이 걸린 방만 찾으므로 남의 방에 들어갈 일은 없다.
        category_manager = CategoryManager(member.guild)
        own_room = category_manager.find_member_room(
            member, settings_manager.get_room_of(guild_id, member.id)
        )
        if own_room and await category_manager.add_member_to_category(own_room, member):
            logger.info(f"✅ 기존 본인 방 복구: {member.name} → {own_room.name}")
            return

        # 방 생성 (같은 이름의 방이 있어도 합류시키지 않고 새로 만든다)
        await build_member_room(member.guild, member, settings_manager)

    except Exception as e:
        logger.error(f"❌ 멤버 입장 처리 오류: {e}", exc_info=True)


@bot.event
async def on_member_remove(member: discord.Member):
    """
    멤버 퇴장 이벤트

    본인 방을 보관(아카이브)한 뒤 삭제한다.
    보관에 실패하면 내용 유실을 막기 위해 삭제하지 않는다.
    방을 함께 쓰는 다른 멤버가 남아 있으면 삭제하지 않는다.
    """
    if member.bot or not guild_allowed(member.guild):
        return

    logger.info(f"👋 멤버 퇴장: {member.name} ({member.id})")

    try:
        guild = member.guild
        guild_id = str(guild.id)

        category_manager = CategoryManager(guild)
        category = category_manager.find_member_room(
            member, settings_manager.get_room_of(guild_id, member.id)
        )

        if not category:
            logger.info(f"퇴장 멤버의 방을 찾지 못함 — 자동 정리 생략: {member.display_name}")
            return

        # 같은 방을 쓰는 다른 멤버가 남아 있으면 방은 그대로 두고 소유자만 넘긴다
        others = category_manager.other_room_members(category, member)
        if others:
            settings_manager.register_room(guild_id, category.id, others[0].id)
            try:
                await category.set_permissions(member, overwrite=None)
            except discord.HTTPException as e:
                logger.warning(f"⚠️ 퇴장 멤버 권한 정리 실패: {e}")
            logger.info(
                f"👥 다른 멤버({others[0].name})가 남아 있어 방 유지: {category.name}"
            )
            return

        # 보관 채널 확인 (없으면 Archiver가 디스크에 저장)
        archive_channel = None
        archive_channel_id = settings_manager.get_archive_channel(guild_id)
        if archive_channel_id:
            archive_channel = guild.get_channel(archive_channel_id)

        # 보관 (실패하면 삭제하지 않음 → 내용 보존)
        try:
            stats = await Archiver.archive(category, archive_channel)
            logger.info(
                f"✅ 방 보관 완료: {category.name} "
                f"(메시지 {stats['messages']}개, 첨부 {stats['attachments']}개, 저장={stats.get('saved')})"
            )
        except Exception as e:
            logger.error(f"❌ 방 보관 실패 — 삭제를 생략합니다: {e}", exc_info=True)
            return

        # 보관 성공 후 삭제
        await category_manager.delete_category(category, delete_channels=True)
        logger.info(f"🗑️ 방 자동 삭제 완료: {category.name}")

    except Exception as e:
        logger.error(f"❌ 멤버 퇴장 처리 오류: {e}", exc_info=True)


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    """방(카테고리)이 어떤 경로로든 삭제되면 소유자 기록도 지운다"""
    if isinstance(channel, discord.CategoryChannel):
        settings_manager.unregister_room(str(channel.guild.id), channel.id)


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
    """봇 시작 전 초기화 (로그인 직후 1회 호출)"""
    # cog들이 공유할 SettingsManager를 봇 인스턴스에 등록한다.
    # (cog가 main을 import하던 순환 참조 패턴 제거)
    bot.settings_manager = settings_manager

    await load_cogs()

    # 슬래시 명령어는 cog 로드 후 여기서 1회만 동기화한다.
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ 슬래시 명령어 동기화: {len(synced)}개")
    except Exception as e:
        logger.error(f"❌ 슬래시 명령어 동기화 실패: {e}", exc_info=True)


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
