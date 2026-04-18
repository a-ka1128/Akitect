"""
방(카테고리) 관련 슬래시 명령어

방 생성, 삭제 등을 담당합니다.
"""
import logging
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

from config import EMBED_SUCCESS_COLOR, EMBED_ERROR_COLOR, CHANNEL_OPERATION_DELAY
from utils import SettingsManager, ChannelManager, CategoryManager, admin_only

logger = logging.getLogger(__name__)


class RoomCog(commands.Cog):
    """방(카테고리) 관리"""

    def __init__(self, bot: commands.Bot, settings: SettingsManager):
        self.bot = bot
        self.settings = settings

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

        # 기존 카테고리 찾기
        category_manager = CategoryManager(interaction.guild)
        category = category_manager.find_category_by_name(target.display_name)

        if category:
            # 기존 카테고리에 멤버 추가
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

        # 새로운 카테고리 생성
        try:
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                target: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    manage_channels=True
                )
            }

            new_category = await category_manager.create_category(
                target.display_name,
                target,
                overwrites
            )

            if not new_category:
                raise Exception("카테고리 생성 실패")

            # 템플릿에 따라 채널 생성
            channel_manager = ChannelManager(interaction.guild)
            template_keys = list(channels.keys())

            for i, (ch_name, ch_info) in enumerate(channels.items()):
                new_channel = await channel_manager.create_in_category(
                    new_category,
                    ch_name,
                    position=i
                )

                if new_channel:
                    # 메시지 전송
                    msg = ch_info.get("msg", "")
                    if msg:
                        embed = discord.Embed(
                            title=ch_name,
                            description=msg,
                            color=EMBED_SUCCESS_COLOR
                        )
                        embed.set_thumbnail(url=target.display_avatar.url)
                        await new_channel.send(embed=embed)

                    # 권한 설정
                    role_id = ch_info.get("role_id")
                    if role_id:
                        role = interaction.guild.get_role(role_id)
                        if role:
                            await channel_manager.set_channel_permissions(
                                new_channel,
                                role,
                                read_messages=True,
                                send_messages=True
                            )

                    await asyncio.sleep(CHANNEL_OPERATION_DELAY)

            # 채널 순서 정렬
            await channel_manager.reorder_channels_in_category(new_category, template_keys)

            embed = discord.Embed(
                title="✅ 방 생성 완료",
                description=f"새로운 카테고리 '{new_category.name}'가 생성되었습니다.",
                color=EMBED_SUCCESS_COLOR
            )
            await interaction.followup.send(embed=embed)
            logger.info(f"방 생성: {target.name} ({target.id})")

        except Exception as e:
            logger.error(f"방 생성 오류: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ 오류",
                description=f"방 생성 중 오류가 발생했습니다: {str(e)}",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="방삭제", description="특정 방(카테고리)을 삭제합니다")
    @app_commands.describe(target_name="삭제할 방의 이름")
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

        # 확인 메시지
        embed = discord.Embed(
            title="⚠️ 확인",
            description=f"'{category.name}' 카테고리를 삭제하겠습니다. "
                       f"이 작업은 되돌릴 수 없습니다.",
            color=discord.Color.orange()
        )

        # 실제 삭제
        success = await category_manager.delete_category(category, delete_channels=True)

        if success:
            embed = discord.Embed(
                title="🗑️ 삭제 완료",
                description=f"'{category.name}' 카테고리가 삭제되었습니다.",
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


async def setup(bot: commands.Bot):
    """Cog 로드"""
    settings = SettingsManager()
    await bot.add_cog(RoomCog(bot, settings))
