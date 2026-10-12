"""
방(카테고리) 관련 슬래시 명령어

방 생성, 삭제 등을 담당합니다.
"""
import logging
import discord
from discord.ext import commands
from discord import app_commands

from config import EMBED_SUCCESS_COLOR, EMBED_ERROR_COLOR
from utils import SettingsManager, CategoryManager, Archiver, admin_only, is_admin, build_member_room

logger = logging.getLogger(__name__)


class RoomCog(commands.Cog):
    """방(카테고리) 관리"""

    def __init__(self, bot: commands.Bot, settings: SettingsManager):
        self.bot = bot
        self.settings = settings

    async def room_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """멤버 방 이름 자동완성 (공지 등 고정 카테고리는 제외)"""
        # 자동완성에는 admin_only 검사가 적용되지 않으므로 직접 막는다
        if not is_admin(interaction):
            return []
        rooms = CategoryManager(interaction.guild).member_rooms()
        return [
            app_commands.Choice(name=c.name, value=c.name)
            for c in rooms
            if current.lower() in c.name.lower()
        ][:25]

    @app_commands.command(name="방생성", description="특정 사용자를 위한 새로운 방을 생성합니다")
    @app_commands.describe(target="방을 생성할 사용자")
    @admin_only()
    async def manual_create_room(
        self,
        interaction: discord.Interaction,
        target: discord.Member
    ):
        """
        수동으로 사용자 방 생성

        같은 이름의 멤버 방이 있으면 그 방에 합류시킨다 (부계정 등).

        Args:
            interaction: Discord Interaction
            target: 방을 생성할 멤버
        """
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        channels = self.settings.get_channels(guild_id)

        if not channels:
            embed = discord.Embed(
                title="❌ 오류",
                description="설정된 채널 템플릿이 없습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        category_manager = CategoryManager(interaction.guild)

        # 이미 본인 방이 있으면 새로 만들지 않는다
        own_room = category_manager.find_member_room(
            target, self.settings.get_room_of(guild_id, target.id)
        )
        if own_room:
            await category_manager.add_member_to_category(own_room, target)
            embed = discord.Embed(
                title="ℹ️ 이미 방이 있습니다",
                description=f"'{own_room.name}' 방에 접근 권한을 다시 확인했습니다.",
                color=EMBED_SUCCESS_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        # 같은 이름의 '멤버 방'이 있으면 합류 (부계정 등 — 관리자가 직접 실행할 때만)
        # 입장 시 자동 생성에서는 합류시키지 않는다 (같은 이름으로 들어와 남의 방을 보는 것 방지)
        # 공지 같은 고정 카테고리는 이름이 같아도 합류시키지 않는다.
        category = category_manager.find_category_by_name(target.display_name)
        if category and category_manager.is_member_room(category):
            success = await category_manager.add_member_to_category(category, target)
            if success:
                embed = discord.Embed(
                    title="✅ 완료",
                    description=f"'{category.name}' 그룹에 멤버로 추가되었습니다.",
                    color=EMBED_SUCCESS_COLOR
                )
            else:
                embed = discord.Embed(
                    title="❌ 오류",
                    description="권한을 설정할 수 없습니다.",
                    color=EMBED_ERROR_COLOR
                )
            await interaction.followup.send(embed=embed)
            return

        # 새 방 생성
        success, message = await build_member_room(interaction.guild, target, self.settings)
        embed = discord.Embed(
            title="✅ 방 생성 완료" if success else "❌ 오류",
            description=message,
            color=EMBED_SUCCESS_COLOR if success else EMBED_ERROR_COLOR
        )
        await interaction.followup.send(embed=embed)
        if success:
            logger.info(f"방 생성: {target.name} ({target.id})")

    @app_commands.command(name="방삭제", description="특정 방(카테고리)을 보관한 뒤 삭제합니다")
    @app_commands.describe(target_name="삭제할 방의 이름")
    @app_commands.autocomplete(target_name=room_autocomplete)
    @admin_only()
    async def delete_room(
        self,
        interaction: discord.Interaction,
        target_name: str
    ):
        """
        방 삭제

        Args:
            interaction: Discord Interaction
            target_name: 삭제할 카테고리 이름
        """
        await interaction.response.defer(ephemeral=True)

        category_manager = CategoryManager(interaction.guild)
        category = category_manager.find_category_by_name(target_name)

        if not category:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"'{target_name}' 카테고리를 찾을 수 없습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        # 공지·관리용 고정 카테고리는 이 명령어로 지우지 않는다 (오타 한 번에 날아가는 것 방지)
        if not category_manager.is_member_room(category):
            embed = discord.Embed(
                title="❌ 멤버 방이 아닙니다",
                description=(
                    f"'{category.name}' 은(는) 멤버 방이 아니라서 삭제하지 않았습니다.\n"
                    f"고정 카테고리는 디스코드에서 직접 삭제하세요."
                ),
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        # 삭제 전 보관 (보관 채널 설정 시 채널에, 없으면 디스크에 저장)
        guild_id = str(interaction.guild_id)
        archive_channel = None
        archive_channel_id = self.settings.get_archive_channel(guild_id)
        if archive_channel_id:
            archive_channel = interaction.guild.get_channel(archive_channel_id)

        try:
            stats = await Archiver.archive(category, archive_channel)
            where = "보관 채널" if stats.get("saved") == "channel" else "서버 디스크"
            archived_note = (
                f"\n📦 보관 완료 ({where}): 메시지 {stats['messages']}개 · 첨부 {stats['attachments']}개"
            )
        except Exception as e:
            # 퇴장 자동 삭제와 같은 정책: 보관에 실패하면 내용 보존을 위해 삭제하지 않는다
            logger.error(f"방 보관 실패 — 삭제 중단: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ 보관 실패 — 삭제하지 않았습니다",
                description=f"'{category.name}' 보관 중 오류가 발생했습니다: {e}",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        # 실제 삭제 (되돌릴 수 없는 작업)
        success = await category_manager.delete_category(category, delete_channels=True)

        if success:
            embed = discord.Embed(
                title="🗑️ 삭제 완료",
                description=f"'{category.name}' 카테고리가 삭제되었습니다.{archived_note}",
                color=EMBED_SUCCESS_COLOR
            )
            logger.info(f"방 삭제: {category.name}")
        else:
            embed = discord.Embed(
                title="❌ 오류",
                description="카테고리 삭제에 실패했습니다.",
                color=EMBED_ERROR_COLOR
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="방정렬",
        description="멤버 방(카테고리)을 이름순(숫자→abc→가나다)으로 정렬합니다"
    )
    @admin_only()
    async def sort_rooms(self, interaction: discord.Interaction):
        """방 이름순 정렬 (고정 카테고리는 제자리 유지)"""
        await interaction.response.defer(ephemeral=True)

        moved = await CategoryManager(interaction.guild).sort_rooms()

        if moved < 0:
            embed = discord.Embed(
                title="❌ 오류",
                description="정렬에 실패했습니다. 봇에 채널 관리 권한이 있는지 확인하세요.",
                color=EMBED_ERROR_COLOR
            )
        elif moved == 0:
            embed = discord.Embed(
                title="✅ 정렬 완료",
                description="이미 이름순으로 정렬되어 있습니다.",
                color=EMBED_SUCCESS_COLOR
            )
        else:
            embed = discord.Embed(
                title="✅ 정렬 완료",
                description=f"방 {moved}개의 위치를 이름순으로 바꿨습니다.",
                color=EMBED_SUCCESS_COLOR
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="방보관",
        description="방(카테고리) 대화를 삭제하지 않고 보관본으로 추출합니다"
    )
    @app_commands.describe(target_name="보관할 방 이름")
    @app_commands.autocomplete(target_name=room_autocomplete)
    @admin_only()
    async def archive_room(
        self,
        interaction: discord.Interaction,
        target_name: str
    ):
        """방 보관 (삭제 없이 추출)"""
        await interaction.response.defer(ephemeral=True)

        category_manager = CategoryManager(interaction.guild)
        category = category_manager.find_category_by_name(target_name)

        if not category:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"'{target_name}' 카테고리를 찾을 수 없습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        guild_id = str(interaction.guild_id)
        archive_channel = None
        archive_channel_id = self.settings.get_archive_channel(guild_id)
        if archive_channel_id:
            archive_channel = interaction.guild.get_channel(archive_channel_id)

        await interaction.followup.send(
            f"📦 `{category.name}` 보관 중... (메시지가 많으면 시간이 걸릴 수 있어요)"
        )

        try:
            stats = await Archiver.archive(category, archive_channel)
            where = ("보관 채널" if stats.get("saved") == "channel"
                     else f"서버 디스크 (`{stats.get('path', '')}`)")
            embed = discord.Embed(
                title="✅ 보관 완료",
                description=(
                    f"방: `{category.name}`\n"
                    f"채널 {stats['channels']}개 · 메시지 {stats['messages']}개 · 첨부 {stats['attachments']}개\n"
                    f"저장 위치: {where}"
                ),
                color=EMBED_SUCCESS_COLOR
            )
        except Exception as e:
            logger.error(f"방 보관 오류: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ 오류",
                description=f"보관 중 오류가 발생했습니다: {str(e)}",
                color=EMBED_ERROR_COLOR
            )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Cog 로드"""
    # main.setup_hook에서 bot에 등록한 공유 SettingsManager 사용
    await bot.add_cog(RoomCog(bot, bot.settings_manager))
