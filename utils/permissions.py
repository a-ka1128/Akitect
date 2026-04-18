"""
권한 검증 및 데코레이터
"""
import logging
import discord
from discord.ext import commands
from discord import app_commands
from config import ALLOWED_USER_IDS, EMBED_ERROR_COLOR

logger = logging.getLogger(__name__)


def is_admin(interaction: discord.Interaction) -> bool:
    """
    사용자가 관리자 권한을 가지고 있는지 확인

    서버 관리자 또는 허용된 사용자 ID에 포함되어 있으면 True

    Args:
        interaction: Discord Interaction 객체

    Returns:
        관리자 여부
    """
    return (
        interaction.user.guild_permissions.administrator or
        interaction.user.id in ALLOWED_USER_IDS
    )


def admin_only():
    """
    데코레이터: 관리자만 사용 가능하도록 제한

    사용 예시:
        @bot.tree.command(name="test")
        @admin_only()
        async def test_cmd(interaction: discord.Interaction):
            ...

    Returns:
        권한 확인 데코레이터
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        if not is_admin(interaction):
            embed = discord.Embed(
                title="❌ 권한 없음",
                description="이 명령어는 관리자만 사용할 수 있습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.warning(
                f"⚠️ 권한 없는 사용자 접근 시도: {interaction.user.name} "
                f"({interaction.user.id}) - {interaction.command.name}"
            )
            return False
        return True

    return app_commands.check(predicate)
