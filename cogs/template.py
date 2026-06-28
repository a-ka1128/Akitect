"""
템플릿 관련 슬래시 명령어

채널 템플릿의 생성, 수정, 삭제, 순서 변경 등을 담당합니다.
"""
import logging
import os
import uuid
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands

import config
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

        # 삭제 전, 첨부 파일 물리 삭제를 위해 정보 확보
        info = self.settings.get_channel(guild_id, channel_name)
        files_to_remove = info.get("files", []) if info else []

        if self.settings.delete_channel(guild_id, channel_name):
            for f in files_to_remove:
                self._delete_physical_file(f.get("path", ""))
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
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.InteractionResponded:
            # Interaction이 이미 응답된 경우 무시
            logger.debug("Interaction이 이미 응답되었습니다.")
            return
        except Exception as e:
            logger.error(f"❌ Interaction 응답 오류: {e}")
            return

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

            file_str = ""
            files = info.get("files", [])
            if files:
                file_str = "   📎 " + ", ".join(f["name"] for f in files) + "\n"

            desc += f"**{i}. {name}**{role_str}\n"
            desc += f"   ```{msg_preview}```\n"
            desc += file_str

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
        self.settings.set_channels(guild_id, new_channels)

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

    # ================================================================
    # 첨부 파일 관련 명령어
    # ================================================================

    async def file_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """선택한 채널 템플릿의 첨부 파일 이름 자동완성"""
        guild_id = str(interaction.guild_id)
        channel_name = getattr(interaction.namespace, "channel_name", None)
        if not channel_name:
            return []
        info = self.settings.get_channel(guild_id, channel_name) or {}
        files = info.get("files", [])
        return [
            app_commands.Choice(name=f["name"], value=f["name"])
            for f in files
            if current.lower() in f["name"].lower()
        ][:25]

    @staticmethod
    def _delete_physical_file(rel_path: str):
        """저장된 첨부 파일을 디스크에서 삭제"""
        if not rel_path:
            return
        try:
            path = Path(rel_path)
            if not path.is_absolute():
                path = config.BASE_DIR / path
            if path.exists():
                os.remove(path)
                logger.info(f"🗑️ 첨부 파일 삭제: {rel_path}")
        except OSError as e:
            logger.error(f"❌ 첨부 파일 삭제 오류: {e}")

    @app_commands.command(
        name="템플릿파일추가",
        description="채널 템플릿에 함께 전송할 파일을 첨부합니다"
    )
    @app_commands.describe(
        channel_name="대상 채널 템플릿 이름",
        file="첨부할 파일"
    )
    @app_commands.autocomplete(channel_name=channel_autocomplete)
    @admin_only()
    async def add_template_file(
        self,
        interaction: discord.Interaction,
        channel_name: str,
        file: discord.Attachment
    ):
        """템플릿 채널에 첨부 파일 추가"""
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

        # 서버 업로드 한도 확인: 봇은 서버 부스트 등급 한도까지만 파일을 재전송할 수 있다.
        # (관리자가 Nitro로 한도보다 큰 파일을 올리면 나중에 방 생성 시 413이 나므로 미리 막는다)
        limit = interaction.guild.filesize_limit
        if file.size > limit:
            embed = discord.Embed(
                title="❌ 파일이 너무 큽니다",
                description=(
                    f"이 서버의 업로드 한도는 **{limit / (1024 * 1024):.0f}MB**입니다.\n"
                    f"`{file.filename}` 은(는) **{file.size / (1024 * 1024):.1f}MB** 라 등록할 수 없습니다.\n\n"
                    f"더 작은 파일로 올리거나, 서버 부스트로 한도를 올려주세요."
                ),
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        # 파일 저장: 디스크에는 UUID 이름으로 저장해 한글/이모지 파일명 충돌을 방지하고,
        # 원본 파일명은 settings.json에 기록해 전송 시 그대로 사용한다.
        try:
            guild_dir = config.TEMPLATE_FILES_DIR / guild_id
            guild_dir.mkdir(parents=True, exist_ok=True)

            suffix = Path(file.filename).suffix
            stored = guild_dir / f"{uuid.uuid4().hex}{suffix}"
            await file.save(stored)

            file_info = {
                "name": file.filename,
                "path": stored.relative_to(config.BASE_DIR).as_posix(),
                "size": file.size,
            }
            self.settings.add_file_to_channel(guild_id, channel_name, file_info)

        except Exception as e:
            logger.error(f"❌ 파일 저장 오류: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ 오류",
                description=f"파일 저장 중 오류가 발생했습니다: {str(e)}",
                color=EMBED_ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
            return

        size_kb = file.size / 1024
        embed = discord.Embed(
            title="✅ 파일 첨부 완료",
            description=f"📝 채널: `{channel_name}`\n📎 파일: `{file.filename}` ({size_kb:.1f} KB)",
            color=EMBED_SUCCESS_COLOR
        )
        embed.set_footer(text="이후 생성되는 방의 해당 채널에 함께 전송됩니다.")
        await interaction.followup.send(embed=embed)
        logger.info(f"템플릿 파일 추가: {guild_id} - {channel_name} - {file.filename}")

    @app_commands.command(
        name="템플릿파일삭제",
        description="채널 템플릿에 첨부된 파일을 삭제합니다"
    )
    @app_commands.describe(
        channel_name="대상 채널 템플릿 이름",
        file_name="삭제할 파일 이름"
    )
    @app_commands.autocomplete(channel_name=channel_autocomplete, file_name=file_autocomplete)
    @admin_only()
    async def delete_template_file(
        self,
        interaction: discord.Interaction,
        channel_name: str,
        file_name: str
    ):
        """템플릿 채널의 첨부 파일 삭제"""
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        removed = self.settings.remove_file_from_channel(guild_id, channel_name, file_name)

        if removed:
            self._delete_physical_file(removed.get("path", ""))
            embed = discord.Embed(
                title="🗑️ 파일 삭제 완료",
                description=f"📝 채널: `{channel_name}`\n📎 파일: `{file_name}`",
                color=EMBED_SUCCESS_COLOR
            )
        else:
            embed = discord.Embed(
                title="❌ 오류",
                description=f"`{channel_name}`에서 `{file_name}` 파일을 찾을 수 없습니다.",
                color=EMBED_ERROR_COLOR
            )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Cog 로드"""
    # main.setup_hook에서 bot에 등록한 공유 SettingsManager 사용
    await bot.add_cog(TemplateCog(bot, bot.settings_manager))