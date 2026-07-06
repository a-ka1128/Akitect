"""
정기 유지보수 — 특정 채널(음성/텍스트)의 메시지를 주기적으로 자동 삭제(청소)

30분마다 점검하여, 채널별로 지정한 주기가 지났으면 메시지를 비운다.
마지막 청소 시각을 settings.json에 저장하므로 봇을 재시작해도 타이머가 유지된다.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Union

import discord
from discord.ext import commands, tasks
from discord import app_commands

from config import EMBED_SUCCESS_COLOR, EMBED_ERROR_COLOR, EMBED_INFO_COLOR
from utils import SettingsManager, admin_only

logger = logging.getLogger(__name__)

# 자동 청소 대상으로 지정할 수 있는 채널 타입 (음성 채팅방 = VoiceChannel)
ClearableChannel = Union[discord.VoiceChannel, discord.TextChannel]


class MaintenanceCog(commands.Cog):
    """주기적 채널 청소"""

    def __init__(self, bot: commands.Bot, settings: SettingsManager):
        self.bot = bot
        self.settings = settings
        self.auto_clear_loop.start()

    def cog_unload(self):
        self.auto_clear_loop.cancel()

    # ------------------------------------------------------------------
    # 백그라운드 루프
    # ------------------------------------------------------------------
    @tasks.loop(minutes=30)
    async def auto_clear_loop(self):
        """30분마다 각 길드의 자동 청소 대상을 점검하고, 주기가 지났으면 비운다."""
        now = datetime.now(timezone.utc)
        for guild in self.bot.guilds:
            gid = str(guild.id)
            entries = self.settings.get_auto_clear(gid)
            for cid, info in list(entries.items()):
                interval = timedelta(hours=info.get("interval_hours", 48))
                last = info.get("last_cleared")
                if last:
                    try:
                        if now - datetime.fromisoformat(last) < interval:
                            continue  # 아직 주기 안 됨
                    except ValueError:
                        pass  # 시각 파싱 실패 시 그냥 청소 진행

                channel = guild.get_channel(int(cid))
                if channel is None:
                    continue  # 삭제된 채널 등

                # 음성 채널에 접속자가 있으면 이번 주기는 건너뛴다.
                # last_cleared를 갱신하지 않으므로, 사람이 나가면 다음 점검(최대 30분 뒤)에 바로 청소됨.
                if isinstance(channel, discord.VoiceChannel) and channel.members:
                    logger.info(
                        f"⏳ 청소 보류 — 음성 접속자 {len(channel.members)}명: {channel.name}"
                    )
                    continue

                await self._purge(channel)
                self.settings.set_auto_clear_time(gid, cid, now.isoformat())

    @auto_clear_loop.before_loop
    async def before_auto_clear(self):
        await self.bot.wait_until_ready()

    async def _purge(self, channel: ClearableChannel) -> int:
        """채널의 (고정되지 않은) 메시지를 삭제하고 삭제 개수를 반환."""
        try:
            deleted = await channel.purge(limit=None, check=lambda m: not m.pinned)
            logger.info(f"🧹 자동 청소: {channel.name} - {len(deleted)}개 삭제")
            return len(deleted)
        except discord.Forbidden:
            logger.error(f"❌ 청소 권한 부족(메시지 관리 권한 필요): {channel.name}")
            return -1
        except Exception as e:
            logger.error(f"❌ 청소 오류 ({channel.name}): {e}")
            return -1

    # ------------------------------------------------------------------
    # 명령어
    # ------------------------------------------------------------------
    @app_commands.command(
        name="자동청소설정",
        description="채널 메시지를 N일마다 자동으로 비웁니다 (고정 메시지는 유지)"
    )
    @app_commands.describe(
        channel="자동 청소할 채널 (음성/텍스트)",
        interval_days="며칠마다 비울지 (기본 2일)"
    )
    @admin_only()
    async def set_auto_clear(
        self,
        interaction: discord.Interaction,
        channel: ClearableChannel,
        interval_days: int = 2
    ):
        """채널 자동 청소 설정"""
        await interaction.response.defer(ephemeral=True)

        if interval_days < 1 or interval_days > 365:
            embed = discord.Embed(
                title="❌ 오류",
                description="주기는 1~365일 사이여야 합니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        guild_id = str(interaction.guild_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        self.settings.set_auto_clear(guild_id, channel.id, interval_days * 24, now_iso)

        embed = discord.Embed(
            title="✅ 자동 청소 설정 완료",
            description=(
                f"채널: {channel.mention}\n"
                f"주기: **{interval_days}일**마다\n"
                f"첫 청소: 약 {interval_days}일 후\n\n"
                f"📌 고정(핀)된 메시지는 지우지 않습니다.\n"
                f"🔊 음성 채널에 **사람이 있으면 건너뛰고**, 비워진 뒤 자동으로 청소합니다.\n"
                f"⚠️ 봇에게 해당 채널의 **메시지 관리** 권한이 필요합니다."
            ),
            color=EMBED_SUCCESS_COLOR
        )
        await interaction.followup.send(embed=embed)
        logger.info(f"자동 청소 설정: {interaction.guild.name} - {channel.name} ({interval_days}일)")

    @app_commands.command(name="자동청소해제", description="채널의 자동 청소를 해제합니다")
    @app_commands.describe(channel="해제할 채널")
    @admin_only()
    async def unset_auto_clear(
        self,
        interaction: discord.Interaction,
        channel: ClearableChannel
    ):
        """채널 자동 청소 해제"""
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)

        if self.settings.remove_auto_clear(guild_id, channel.id):
            embed = discord.Embed(
                title="🗑️ 해제 완료",
                description=f"{channel.mention} 자동 청소를 해제했습니다.",
                color=EMBED_SUCCESS_COLOR
            )
        else:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"{channel.mention}은(는) 자동 청소 대상이 아닙니다.",
                color=EMBED_ERROR_COLOR
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="자동청소목록", description="자동 청소 중인 채널을 확인합니다")
    @admin_only()
    async def list_auto_clear(self, interaction: discord.Interaction):
        """자동 청소 목록"""
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        entries = self.settings.get_auto_clear(guild_id)

        if not entries:
            embed = discord.Embed(
                title="📭 없음",
                description="자동 청소 중인 채널이 없습니다.",
                color=discord.Color.greyple()
            )
            await interaction.followup.send(embed=embed)
            return

        desc = ""
        for cid, info in entries.items():
            ch = interaction.guild.get_channel(int(cid))
            name = ch.mention if ch else f"(삭제된 채널 {cid})"
            days = info.get("interval_hours", 48) / 24
            desc += f"• {name} — **{days:g}일**마다\n"

        embed = discord.Embed(
            title="🧹 자동 청소 목록",
            description=desc,
            color=EMBED_INFO_COLOR
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="지금청소",
        description="채널 메시지를 지금 즉시 비웁니다 (고정 메시지는 유지)"
    )
    @app_commands.describe(channel="지금 비울 채널")
    @admin_only()
    async def clear_now(
        self,
        interaction: discord.Interaction,
        channel: ClearableChannel
    ):
        """즉시 청소 (테스트/수동)"""
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"🧹 {channel.mention} 청소 중...")

        count = await self._purge(channel)

        # 자동 청소 대상이면 타이머도 리셋
        guild_id = str(interaction.guild_id)
        if str(channel.id) in self.settings.get_auto_clear(guild_id):
            self.settings.set_auto_clear_time(
                guild_id, str(channel.id), datetime.now(timezone.utc).isoformat()
            )

        if count < 0:
            embed = discord.Embed(
                title="❌ 청소 실패",
                description=f"{channel.mention} 청소 중 오류(권한 등). 봇의 **메시지 관리** 권한을 확인하세요.",
                color=EMBED_ERROR_COLOR
            )
        else:
            embed = discord.Embed(
                title="✅ 청소 완료",
                description=f"{channel.mention}에서 **{count}개** 메시지를 삭제했습니다.",
                color=EMBED_SUCCESS_COLOR
            )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Cog 로드"""
    # main.setup_hook에서 bot에 등록한 공유 SettingsManager 사용
    await bot.add_cog(MaintenanceCog(bot, bot.settings_manager))
