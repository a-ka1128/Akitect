"""
Discord 카테고리(카테고리=방) 관리
"""
import asyncio
import logging
from typing import Optional, Dict, Any

import discord
from config import CHANNEL_OPERATION_DELAY

logger = logging.getLogger(__name__)


class CategoryManager:
    """
    Discord 카테고리를 관리하는 클래스

    카테고리 생성, 권한 설정, 삭제 등의 작업을 수행합니다.
    """

    def __init__(self, guild: discord.Guild):
        """
        CategoryManager 초기화

        Args:
            guild: 작업할 Discord Guild
        """
        self.guild = guild
        logger.info(f"CategoryManager 초기화: {guild.name}")

    def find_category_by_name(self, name: str) -> Optional[discord.CategoryChannel]:
        """
        이름으로 카테고리 찾기

        정확한 이름 일치 또는 부분 일치로 찾습니다.

        Args:
            name: 찾을 카테고리 이름

        Returns:
            찾은 카테고리, 또는 None
        """
        # 정확한 이름 찾기
        category = discord.utils.get(self.guild.categories, name=name)
        if category:
            return category

        # 부분 일치 찾기
        for cat in self.guild.categories:
            if cat.name and name in cat.name:
                return cat

        return None

    async def create_category(
        self,
        name: str,
        member: discord.Member,
        overwrites: Optional[Dict] = None
    ) -> Optional[discord.CategoryChannel]:
        """
        새로운 카테고리 생성

        Args:
            name: 카테고리 이름
            member: 카테고리에 추가할 멤버
            overwrites: 권한 설정 (선택사항)

        Returns:
            생성된 카테고리, 또는 실패 시 None
        """
        # 이미 존재하는 카테고리 확인
        existing = discord.utils.get(self.guild.categories, name=name)
        if existing:
            logger.warning(f"⚠️ 카테고리가 이미 존재합니다: {name}")
            return existing

        try:
            # 기본 권한 설정
            if overwrites is None:
                overwrites = {
                    self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    self.guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True)
                }

            new_category = await self.guild.create_category(
                name=name,
                overwrites=overwrites
            )
            logger.info(f"✅ 카테고리 생성 완료: {new_category.name}")
            return new_category

        except discord.Forbidden:
            logger.error(f"❌ 권한 부족: 카테고리를 생성할 수 없습니다")
            return None
        except discord.HTTPException as e:
            logger.error(f"❌ Discord API 오류: {e.status} {e.text}")
            return None
        except Exception as e:
            logger.error(f"❌ 카테고리 생성 오류: {e}", exc_info=True)
            return None

    async def set_category_permissions(
        self,
        category: discord.CategoryChannel,
        member: discord.Member,
        **permissions: bool
    ) -> bool:
        """
        카테고리에 대한 멤버의 권한 설정

        Args:
            category: 대상 카테고리
            member: 권한을 설정할 멤버
            **permissions: 권한 설정 (read_messages=True 등)

        Returns:
            성공 여부
        """
        try:
            await category.set_permissions(member, **permissions)
            logger.info(f"✅ 카테고리 권한 설정: {category.name} - {member.name}")
            return True

        except discord.Forbidden:
            logger.error(f"❌ 권한 부족: 카테고리 권한을 설정할 수 없습니다")
            return False
        except Exception as e:
            logger.error(f"❌ 권한 설정 오류: {e}", exc_info=True)
            return False

    async def add_member_to_category(
        self,
        category: discord.CategoryChannel,
        member: discord.Member
    ) -> bool:
        """
        카테고리에 멤버 추가 (권한 부여)

        Args:
            category: 대상 카테고리
            member: 추가할 멤버

        Returns:
            성공 여부
        """
        return await self.set_category_permissions(
            category,
            member,
            read_messages=True,
            send_messages=True
        )

    async def delete_category(
        self,
        category: discord.CategoryChannel,
        delete_channels: bool = True
    ) -> bool:
        """
        카테고리 삭제

        Args:
            category: 삭제할 카테고리
            delete_channels: 카테고리 내 채널도 함께 삭제할지 여부

        Returns:
            성공 여부
        """
        try:
            logger.info(f"카테고리 삭제 시작: {category.name}")

            # 채널 삭제 (선택사항)
            if delete_channels:
                channels = list(category.channels)
                for channel in channels:
                    try:
                        await channel.delete()
                        logger.debug(f"채널 삭제: {channel.name}")
                        await asyncio.sleep(CHANNEL_OPERATION_DELAY)
                    except Exception as e:
                        logger.error(f"❌ 채널 삭제 오류 ({channel.name}): {e}")

            # 카테고리 삭제
            await category.delete()
            logger.info(f"✅ 카테고리 삭제 완료: {category.name}")
            return True

        except discord.Forbidden:
            logger.error(f"❌ 권한 부족: 카테고리를 삭제할 수 없습니다")
            return False
        except Exception as e:
            logger.error(f"❌ 카테고리 삭제 오류: {e}", exc_info=True)
            return False

    async def rename_category(
        self,
        category: discord.CategoryChannel,
        new_name: str
    ) -> bool:
        """
        카테고리 이름 변경

        Args:
            category: 대상 카테고리
            new_name: 새 이름

        Returns:
            성공 여부
        """
        try:
            old_name = category.name
            await category.edit(name=new_name)
            logger.info(f"✅ 카테고리 이름 변경: {old_name} → {new_name}")
            return True

        except discord.Forbidden:
            logger.error(f"❌ 권한 부족: 카테고리 이름을 변경할 수 없습니다")
            return False
        except Exception as e:
            logger.error(f"❌ 이름 변경 오류: {e}", exc_info=True)
            return False
