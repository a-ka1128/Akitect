"""
템플릿 관련 슬래시 명령어

채널 템플릿의 생성, 수정, 삭제, 순서 변경 등을 담당합니다.
"""
import logging
import discord
from discord.ext import commands
from discord import app_commands

from config import EMBED_SUCCESS_COLOR, EMBED_ERROR_COLOR, EMBED_INFO_COLOR
from utils import SettingsManager, Validators, admin_only

logger = logging.getLogger(__name__)


class TemplateCog(commands.Cog):
    """채널 템플릿 관리"""

    def __init__(self, bot: commands.Bot, settings: SettingsManager):
        self.bot = bot
        self.settings = settings

    async def channel_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """
        채널 이름 자동완성

        Args:
            interaction: Discord Interaction
            current: 현재 입력한 텍스트

        Returns:
            자동완성 옵션 리스트
        """
        guild_id = str(interaction.guild_id)
        channels = self.settings.get_channels(guild_id)

        # 현재 입력값으로 필터링
        filtered = [
            name for name in channels.keys()
            if current.lower() in name.lower()
        ]

        return [
            app_commands.Choice(name=name, value=name)
            for name in filtered[:25]  # Discord는 최대 25개까지만 허용
        ]

    @app_commands.command(name="템플릿생성", description="새로운 채널 템플릿을 추가합니다")
    @app_commands.describe(
        channel_name="생성할 채널 템플릿 이름",
        message="채널에 표시할 안내 메시지",
        view_role="채널 열람 가능 역할 (선택사항)"
    )
    @admin_only()
    async def create_template(
        self,
        interaction: discord.Interaction,
        channel_name: str,
        message: str,
        view_role: discord.Role = None
    ):
        """
        새로운 채널 템플릿 생성

        Args:
            interaction: Discord Interaction
            channel_name: 채널 템플릿 이름
            message: 채널 설명 메시지
            view_role: 채널 열람 가능 역할
        """
        await interaction.response.defer(ephemeral=True)

        # 입력값 검증
        valid, error = Validators.validate_channel_name(channel_name)
        if not valid:
            embed = discord.Embed(
                title="❌ 오류",
                description=error,
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        valid, error = Validators.validate_message(message)
        if not valid:
            embed = discord.Embed(
                title="❌ 오류",
                description=error,
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        # 템플릿 저장
        guild_id = str(interaction.guild_id)
        info = {"msg": message.replace("\\n", "\n")}

        if view_role:
            info["role_id"] = view_role.id

        self.settings.set_channel(guild_id, channel_name, info)

        # 성공 응답
        role_str = f"\n🔒 권한: {view_role.mention}" if view_role else ""
        embed = discord.Embed(
            title="✅ 템플릿 생성 완료",
            description=f"📝 채널: `{channel_name}`{role_str}",
            color=EMBED_SUCCESS_COLOR
        )
        await interaction.followup.send(embed=embed)
        logger.info(f"템플릿 생성: {guild_id} - {channel_name}")

    @app_commands.command(name="템플릿수정", description="기존 채널 템플릿을 수정합니다")
    @app_commands.describe(
        channel_name="수정할 템플릿 이름",
        message="새 안내 메시지",
        view_role="새 열람 역할"
    )
    @app_commands.autocomplete(channel_name=channel_autocomplete)
    @admin_only()
    async def modify_template(
        self,
        interaction: discord.Interaction,
        channel_name: str,
        message: str = None,
        view_role: discord.Role = None
    ):
        """
        기존 템플릿 수정

        Args:
            interaction: Discord Interaction
            channel_name: 수정할 템플릿 이름
            message: 새 메시지 (선택사항)
            view_role: 새 역할 (선택사항)
        """
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        info = self.settings.get_channel(guild_id, channel_name)

        if not info:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"`{channel_name}` 템플릿을 찾을 수 없습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        # 메시지 업데이트
        result_msg = f"🔄 **수정 완료!**\n📂 대상: `{channel_name}`"

        if message:
            valid, error = Validators.validate_message(message)
            if not valid:
                embed = discord.Embed(
                    title="❌ 오류",
                    description=error,
                    color=EMBED_ERROR_COLOR
                )
                await interaction.followup.send(embed=embed)
                return

            info["msg"] = message.replace("\\n", "\n")
            result_msg += "\n📝 메시지 업데이트됨"

        # 역할 업데이트
        if view_role:
            info["role_id"] = view_role.id
            result_msg += f"\n🔒 권한: {view_role.mention}"

        self.settings.set_channel(guild_id, channel_name, info)

        embed = discord.Embed(
            title="✅ 수정 완료",
            description=result_msg,
            color=EMBED_SUCCESS_COLOR
        )
        await interaction.followup.send(embed=embed)
        logger.info(f"템플릿 수정: {guild_id} - {channel_name}")

    @app_commands.command(name="템플릿삭제", description="채널 템플릿을 삭제합니다")
    @app_commands.describe(channel_name="삭제할 템플릿 이름")
    @app_commands.autocomplete(channel_name=channel_autocomplete)
    @admin_only()
    async def delete_template(
        self,
        interaction: discord.Interaction,
        channel_name: str
    ):
        """
        템플릿 삭제

        Args:
            interaction: Discord Interaction
            channel_name: 삭제할 템플릿 이름
        """
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)

        if self.settings.delete_channel(guild_id, channel_name):
            embed = discord.Embed(
                title="🗑️ 삭제 완료",
                description=f"`{channel_name}` 템플릿이 삭제되었습니다.",
                color=EMBED_SUCCESS_COLOR
            )
            await interaction.followup.send(embed=embed)
            logger.info(f"템플릿 삭제: {guild_id} - {channel_name}")
        else:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"`{channel_name}` 템플릿을 찾을 수 없습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="템플릿목록", description="현재 서버의 모든 채널 템플릿을 확인합니다")
    async def list_templates(self, interaction: discord.Interaction):
        """
        템플릿 목록 표시

        Args:
            interaction: Discord Interaction
        """
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        channels = self.settings.get_channels(guild_id)

        if not channels:
            embed = discord.Embed(
                title="📭 템플릿 없음",
                description="생성된 템플릿이 없습니다.",
                color=discord.Color.greyple()
            )
            await interaction.followup.send(embed=embed)
            return

        # 템플릿 목록 구성
        desc = ""
        for i, (name, info) in enumerate(channels.items(), 1):
            msg_preview = info.get("msg", "")[:30]
            if len(info.get("msg", "")) > 30:
                msg_preview += "..."

            role_str = ""
            # 여러 역할 지원
            role_ids = info.get("role_ids", [])
            if not role_ids and "role_id" in info:
                role_ids = [info["role_id"]]

            if role_ids:
                roles = []
                for role_id in role_ids:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        roles.append(role.name)
                if roles:
                    role_str = f" [🔒 {', '.join(roles)}]"

            desc += f"**{i}. {name}**{role_str}\n"
            desc += f"   ```{msg_preview}```\n"

        embed = discord.Embed(
            title="📋 채널 템플릿 목록",
            description=desc,
            color=EMBED_INFO_COLOR
        )
        embed.set_footer(text=f"총 {len(channels)}개의 템플릿")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="템플릿순서", description="채널 생성 순서를 변경합니다")
    @app_commands.describe(
        channel_name="변경할 채널 이름",
        order="새로운 순서 (1부터)"
    )
    @app_commands.autocomplete(channel_name=channel_autocomplete)
    @admin_only()
    async def reorder_template(
        self,
        interaction: discord.Interaction,
        channel_name: str,
        order: int
    ):
        """
        템플릿 순서 변경

        Args:
            interaction: Discord Interaction
            channel_name: 순서를 변경할 채널
            order: 새로운 순서 (1부터)
        """
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        channels = self.settings.get_channels(guild_id)

        if channel_name not in channels:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"`{channel_name}` 템플릿을 찾을 수 없습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        # 순서 검증
        valid, error, corrected_order = Validators.validate_order(order, len(channels))
        if not valid:
            embed = discord.Embed(
                title="❌ 오류",
                description=error,
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        # 순서 변경
        keys = list(channels.keys())
        keys.remove(channel_name)
        keys.insert(corrected_order - 1, channel_name)

        # 새로운 채널 딕셔너리 생성 (순서 유지)
        new_channels = {k: channels[k] for k in keys}
        self.settings.data[guild_id]["channels"] = new_channels
        self.settings.save()

        # 결과 출력
        desc = ""
        for i, name in enumerate(keys, 1):
            desc += f"**{i}. {name}**\n"

        embed = discord.Embed(
            title="✅ 순서 변경 완료",
            description=desc,
            color=EMBED_SUCCESS_COLOR
        )
        await interaction.followup.send(embed=embed)
        logger.info(f"템플릿 순서 변경: {guild_id} - {channel_name} → {corrected_order}")

    @app_commands.command(name="역할추가", description="템플릿 채널에 역할을 추가합니다")
    @app_commands.describe(
        channel_name="대상 채널 이름",
        role="추가할 역할"
    )
    @app_commands.autocomplete(channel_name=channel_autocomplete)
    @admin_only()
    async def add_role_to_channel(
        self,
        interaction: discord.Interaction,
        channel_name: str,
        role: discord.Role
    ):
        """
        템플릿 채널에 열람 가능한 역할 추가

        Args:
            interaction: Discord Interaction
            channel_name: 대상 채널 이름
            role: 추가할 역할
        """
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)

        if self.settings.add_role_to_channel(guild_id, channel_name, role.id):
            embed = discord.Embed(
                title="✅ 역할 추가 완료",
                description=f"📝 채널: `{channel_name}`\n🔒 역할: {role.mention}",
                color=EMBED_SUCCESS_COLOR
            )
            await interaction.followup.send(embed=embed)
            logger.info(f"역할 추가: {guild_id} - {channel_name} - {role.id}")
        else:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"`{channel_name}` 채널을 찾을 수 없거나 이미 추가된 역할입니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="역할제거", description="템플릿 채널에서 역할을 제거합니다")
    @app_commands.describe(
        channel_name="대상 채널 이름",
        role="제거할 역할"
    )
    @app_commands.autocomplete(channel_name=channel_autocomplete)
    @admin_only()
    async def remove_role_from_channel(
        self,
        interaction: discord.Interaction,
        channel_name: str,
        role: discord.Role
    ):
        """
        템플릿 채널에서 열람 가능한 역할 제거

        Args:
            interaction: Discord Interaction
            channel_name: 대상 채널 이름
            role: 제거할 역할
        """
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)

        if self.settings.remove_role_from_channel(guild_id, channel_name, role.id):
            embed = discord.Embed(
                title="✅ 역할 제거 완료",
                description=f"📝 채널: `{channel_name}`\n🔒 역할: {role.mention}",
                color=EMBED_SUCCESS_COLOR
            )
            await interaction.followup.send(embed=embed)
            logger.info(f"역할 제거: {guild_id} - {channel_name} - {role.id}")
        else:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"`{channel_name}` 채널을 찾을 수 없거나 해당 역할이 설정되지 않았습니다.",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Cog 로드"""
    # main.py에서 만든 전역 SettingsManager 인스턴스 사용
    import main
    await bot.add_cog(TemplateCog(bot, main.settings_manager))
