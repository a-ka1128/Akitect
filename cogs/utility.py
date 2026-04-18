"""
유틸리티 명령어

역할 설정, 도움 호출, 재시작 등을 담당합니다.
"""
import logging
import os
import sys
import discord
from discord.ext import commands
from discord import app_commands

from config import EMBED_SUCCESS_COLOR, EMBED_ERROR_COLOR, ALLOWED_USER_IDS
from utils import SettingsManager, admin_only

logger = logging.getLogger(__name__)


class UtilityCog(commands.Cog):
    """유틸리티 명령어"""

    def __init__(self, bot: commands.Bot, settings: SettingsManager):
        self.bot = bot
        self.settings = settings

    @app_commands.command(
        name="자동역할설정",
        description="서버에 입장하는 새 멤버에게 자동으로 할당할 역할을 설정합니다"
    )
    @app_commands.describe(role="할당할 역할")
    @admin_only()
    async def set_auto_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """
        자동 할당 역할 설정

        Args:
            interaction: Discord Interaction
            role: 할당할 역할
        """
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        self.settings.set_auto_role(guild_id, role.id)

        embed = discord.Embed(
            title="✅ 설정 완료",
            description=f"새 멤버에게 {role.mention}을(를) 자동으로 할당합니다.",
            color=EMBED_SUCCESS_COLOR
        )
        await interaction.followup.send(embed=embed)
        logger.info(f"자동 역할 설정: {interaction.guild.name} - {role.name}")

    @app_commands.command(
        name="지원역할설정",
        description="관리자 호출 시 핑을 받을 역할을 설정합니다"
    )
    @app_commands.describe(role="핑을 받을 역할")
    @admin_only()
    async def set_support_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """
        지원 역할 설정

        Args:
            interaction: Discord Interaction
            role: 핑을 받을 역할
        """
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        self.settings.set_support_role(guild_id, role.id)

        embed = discord.Embed(
            title="✅ 설정 완료",
            description=f"{role.mention}을(를) 지원 역할로 설정했습니다.",
            color=EMBED_SUCCESS_COLOR
        )
        await interaction.followup.send(embed=embed)
        logger.info(f"지원 역할 설정: {interaction.guild.name} - {role.name}")

    @app_commands.command(
        name="도움",
        description="관리자를 호출합니다"
    )
    async def help_cmd(self, interaction: discord.Interaction):
        """
        관리자 호출

        Args:
            interaction: Discord Interaction
        """
        await interaction.response.defer(ephemeral=False)

        guild_id = str(interaction.guild_id)
        support_role_id = self.settings.get_support_role(guild_id)

        if not support_role_id:
            embed = discord.Embed(
                title="⚠️ 오류",
                description="지원 역할이 설정되지 않았습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        role = interaction.guild.get_role(support_role_id)

        if not role:
            embed = discord.Embed(
                title="⚠️ 오류",
                description="지원 역할을 찾을 수 없습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="📢 도움 요청",
            description=f"{role.mention}님, {interaction.user.mention}님이 도움을 요청했습니다!",
            color=discord.Color.yellow()
        )
        await interaction.followup.send(embed=embed)
        logger.info(f"도움 요청: {interaction.guild.name} - {interaction.user.name}")

    @app_commands.command(
        name="동기화",
        description="슬래시 명령어를 Discord와 동기화합니다"
    )
    @admin_only()
    async def sync(self, interaction: discord.Interaction):
        """
        슬래시 명령어 동기화

        Args:
            interaction: Discord Interaction
        """
        await interaction.response.defer(ephemeral=True)

        try:
            synced = await self.bot.tree.sync()
            embed = discord.Embed(
                title="✅ 동기화 완료",
                description=f"{len(synced)}개의 슬래시 명령어가 동기화되었습니다.",
                color=EMBED_SUCCESS_COLOR
            )
            await interaction.followup.send(embed=embed)
            logger.info(f"슬래시 명령어 동기화 완료: {len(synced)}개")

        except Exception as e:
            logger.error(f"동기화 실패: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ 오류",
                description=f"동기화 중 오류가 발생했습니다: {str(e)}",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="재시작",
        description="봇을 재시작합니다 (소유자만)"
    )
    async def restart_bot(self, interaction: discord.Interaction):
        """
        봇 재시작

        Args:
            interaction: Discord Interaction
        """
        # 소유자 확인
        if interaction.user.id not in ALLOWED_USER_IDS:
            embed = discord.Embed(
                title="❌ 권한 없음",
                description="이 명령어는 봇 소유자만 사용할 수 있습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.send_message(
            "🔄 봇을 재시작하는 중입니다...",
            ephemeral=True
        )

        logger.info("봇 재시작 요청")

        # 프로세스 재시작
        os.execl(sys.executable, sys.executable, *sys.argv)


async def setup(bot: commands.Bot):
    """Cog 로드"""
    # main.py에서 만든 전역 SettingsManager 인스턴스 사용
    import main
    await bot.add_cog(UtilityCog(bot, main.settings_manager))
