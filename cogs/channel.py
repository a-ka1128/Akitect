"""
채널 관련 슬래시 명령어

채널 이름 변경, 추가 배포, 생성, 삭제, 공지 수정 등을 담당합니다.
"""
import logging
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

from config import EMBED_SUCCESS_COLOR, EMBED_ERROR_COLOR, CHANNEL_OPERATION_DELAY
from utils import SettingsManager, ChannelManager, Validators, admin_only

logger = logging.getLogger(__name__)


class ChannelCog(commands.Cog):
    """채널 관리"""

    def __init__(self, bot: commands.Bot, settings: SettingsManager):
        self.bot = bot
        self.settings = settings

    async def channel_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """채널 이름 자동완성"""
        guild_id = str(interaction.guild_id)
        channels = self.settings.get_channels(guild_id)

        filtered = [
            name for name in channels.keys()
            if current.lower() in name.lower()
        ]

        return [
            app_commands.Choice(name=name, value=name)
            for name in filtered[:25]
        ]

    @app_commands.command(
        name="채널이름변경",
        description="서버 전체의 특정 이름 채널을 한 번에 변경합니다"
    )
    @app_commands.describe(
        old_name="현재 채널 이름",
        new_name="새로운 채널 이름"
    )
    @app_commands.autocomplete(old_name=channel_autocomplete)
    @admin_only()
    async def rename_channel_bulk(
        self,
        interaction: discord.Interaction,
        old_name: str,
        new_name: str
    ):
        """
        서버 전체 채널 이름 변경

        Args:
            interaction: Discord Interaction
            old_name: 현재 채널 이름
            new_name: 새 채널 이름
        """
        await interaction.response.defer(ephemeral=True)

        # 입력값 검증
        valid, error = Validators.validate_channel_name(new_name)
        if not valid:
            embed = discord.Embed(
                title="❌ 오류",
                description=error,
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        guild_id = str(interaction.guild.id)

        # 1. 템플릿 업데이트 (나중에 들어올 사용자도 새 이름으로 생성되도록)
        if self.settings.rename_channel(guild_id, old_name, new_name):
            logger.info(f"템플릿 업데이트: {old_name} → {new_name}")
        else:
            # 템플릿이 없어도 실제 채널은 변경할 수 있음
            logger.warning(f"템플릿을 찾을 수 없음: {old_name}")

        # 2. 실제 채널 이름 변경
        await interaction.followup.send(
            f"🚀 **서버 전체 스캔 시작!**\n"
            f"모든 카테고리에서 `{old_name}` 채널을 찾아 `{new_name}`(으)로 변경합니다..."
        )

        manager = ChannelManager(interaction.guild)
        count = await manager.rename_bulk(old_name, new_name)

        embed = discord.Embed(
            title="✨ 작업 완료!",
            description=f"총 **{count}**개의 채널 이름을 `{new_name}`(으)로 바꿨습니다.",
            color=EMBED_SUCCESS_COLOR
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="채널추가배포",
        description="새로 만든 템플릿 채널을 기존 모든 방에 추가합니다"
    )
    @app_commands.describe(channel_name="배포할 채널 템플릿 이름")
    @app_commands.autocomplete(channel_name=channel_autocomplete)
    @admin_only()
    async def distribute_new_channel(
        self,
        interaction: discord.Interaction,
        channel_name: str
    ):
        """
        새 템플릿 채널을 모든 방에 배포

        Args:
            interaction: Discord Interaction
            channel_name: 배포할 채널 이름
        """
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild.id)
        channel_info = self.settings.get_channel(guild_id, channel_name)

        if not channel_info:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"`{channel_name}` 템플릿을 찾을 수 없습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        channels = self.settings.get_channels(guild_id)
        template_keys = list(channels.keys())

        try:
            target_index = template_keys.index(channel_name)
        except ValueError:
            target_index = None

        await interaction.followup.send(
            f"🚀 **`{channel_name}`** (위치: {target_index + 1}번째) 배포 시작..."
        )

        manager = ChannelManager(interaction.guild)
        success_count = 0

        # 모든 카테고리에 채널 추가
        for category in interaction.guild.categories:
            if not category:
                continue

            # 이미 존재 확인
            if discord.utils.get(category.text_channels, name=channel_name):
                continue

            try:
                new_channel = await manager.create_in_category(
                    category,
                    channel_name,
                    position=target_index
                )

                if new_channel:
                    # 메시지 전송
                    msg = channel_info.get("msg", "")
                    if msg:
                        # 첫 번째 채널에서만 멤버 태그
                        member_mention = f"{member.mention}" if target_index == 0 else ""

                        message_content = f"{member_mention}".strip() if member_mention else None

                        embed = discord.Embed(
                            title=channel_name,
                            description=msg,
                            color=EMBED_SUCCESS_COLOR
                        )
                        await new_channel.send(content=message_content, embed=embed)

                    # 권한 설정
                    role_id = channel_info.get("role_id")
                    if role_id:
                        role = interaction.guild.get_role(role_id)
                        if role:
                            await manager.set_channel_permissions(
                                new_channel,
                                role,
                                read_messages=True,
                                send_messages=True
                            )

                    success_count += 1
                    await asyncio.sleep(CHANNEL_OPERATION_DELAY)

            except Exception as e:
                logger.error(f"채널 배포 오류 ({category.name}): {e}")

        embed = discord.Embed(
            title="✅ 배포 완료!",
            description=f"총 **{success_count}**개의 카테고리에 작업되었습니다.",
            color=EMBED_SUCCESS_COLOR
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="공지수정",
        description="템플릿 내용으로 기존 공지를 수정합니다"
    )
    @app_commands.describe(channel_name="수정할 채널 이름")
    @app_commands.autocomplete(channel_name=channel_autocomplete)
    @admin_only()
    async def edit_announcement(
        self,
        interaction: discord.Interaction,
        channel_name: str
    ):
        """
        채널의 기존 공지 메시지를 수정

        Args:
            interaction: Discord Interaction
            channel_name: 수정할 채널 이름
        """
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild.id)
        channel_info = self.settings.get_channel(guild_id, channel_name)

        if not channel_info:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"`{channel_name}` 설정이 없습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        new_msg = channel_info.get("msg", "")

        if not new_msg:
            embed = discord.Embed(
                title="❌ 오류",
                description="메시지 내용이 없습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        await interaction.followup.send("✏️ 수정 중...")

        success_count = 0
        create_count = 0

        # 모든 카테고리를 순회
        for category in interaction.guild.categories:
            for channel in category.text_channels:
                if channel_name not in channel.name:
                    continue

                try:
                    new_embed = discord.Embed(
                        title=channel_name,
                        description=new_msg,
                        color=EMBED_SUCCESS_COLOR
                    )
                    new_embed.set_footer(text="내용이 수정되었습니다.")

                    # 기존 메시지 찾기
                    target_msg = None
                    async for msg in channel.history(limit=10):
                        if msg.author == interaction.client.user:
                            target_msg = msg
                            break

                    if target_msg:
                        await target_msg.edit(embed=new_embed)
                        success_count += 1
                    else:
                        await channel.send(embed=new_embed)
                        create_count += 1

                    await asyncio.sleep(CHANNEL_OPERATION_DELAY)

                except discord.Forbidden:
                    logger.error(f"권한 부족: {channel.name}")
                except Exception as e:
                    logger.error(f"공지 수정 오류 ({channel.name}): {e}")

        embed = discord.Embed(
            title="✅ 완료!",
            description=f"수정: {success_count}개 / 신규: {create_count}개",
            color=EMBED_SUCCESS_COLOR
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Cog 로드"""
    # main.py에서 만든 전역 SettingsManager 인스턴스 사용
    import main
    await bot.add_cog(ChannelCog(bot, main.settings_manager))
