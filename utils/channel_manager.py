"""
Discord 채널 관리 (생성, 수정, 삭제 등)
"""
import asyncio
import logging
from typing import Optional, Dict, Any

import discord
from config import CHANNEL_OPERATION_DELAY, RENAME_OPERATION_DELAY

logger = logging.getLogger(__name__)


class ChannelManager:
    """
    Discord 채널 작업을 관리하는 클래스

    채널 생성, 이름 변경, 권한 설정 등의 작업을 수행합니다.
    """

    def __init__(self, guild: discord.Guild):
        """
        ChannelManager 초기화

        Args:
            guild: 작업할 Discord Guild
        """
        self.guild = guild
        logger.info(f"ChannelManager 초기화: {guild.name}")

    async def rename_bulk(self, old_name: str, new_name: str) -> int:
        """
        서버 전체에서 특정 이름의 채널을 찾아 모두 이름 변경

        각 카테고리를 순회하며 old_name을 가진 채널을 찾아 new_name으로 변경합니다.

        Args:
            old_name: 현재 채널 이름
            new_name: 새 채널 이름

        Returns:
            변경된 채널의 개수
        """
        count = 0
        logger.info(f"채널 일괄 이름 변경 시작: {old_name} → {new_name}")

        for category in self.guild.categories:
            if not category:
                continue

            # 카테고리 내에서 old_name을 가진 채널 찾기
            target_channel = discord.utils.get(
                category.text_channels,
                name=old_name
            )

            if not target_channel:
                continue

            try:
                await target_channel.edit(name=new_name)
                logger.info(f"✅ 채널 이름 변경 완료: {old_name} → {new_name}")
                count += 1
                await asyncio.sleep(RENAME_OPERATION_DELAY)

            except discord.Forbidden:
                logger.error(
                    f"❌ 권한 부족: 채널 이름을 변경할 수 없습니다 ({target_channel.name})"
                )
            except discord.NotFound:
                logger.error(f"❌ 채널을 찾을 수 없습니다: {target_channel.name}")
            except discord.HTTPException as e:
                logger.error(f"❌ Discord API 오류: {e.status} {e.text}")
            except Exception as e:
                logger.error(f"❌ 예상치 못한 오류: {e}", exc_info=True)

        logger.info(f"채널 일괄 이름 변경 완료: {count}개 채널 변경됨")
        return count

    async def create_in_category(
        self,
        category: discord.CategoryChannel,
        ch_name: str,
        position: Optional[int] = None,
        **kwargs
    ) -> Optional[discord.TextChannel]:
        """
        특정 카테고리에 채널 생성

        Args:
            category: 대상 카테고리
            ch_name: 생성할 채널 이름
            position: 채널 위치 (선택사항)
            **kwargs: discord.CategoryChannel.create_text_channel() 인자

        Returns:
            생성된 채널, 또는 실패 시 None
        """
        # 이미 존재하는 채널 확인
        existing = discord.utils.get(category.text_channels, name=ch_name)
        if existing:
            logger.warning(f"⚠️ 채널이 이미 존재합니다: {ch_name}")
            return None

        try:
            new_channel = await category.create_text_channel(
                ch_name,
                position=position,
                **kwargs
            )
            logger.info(f"✅ 채널 생성 완료: {new_channel.name}")
            return new_channel

        except discord.Forbidden:
            logger.error(f"❌ 권한 부족: 채널을 생성할 수 없습니다")
            return None
        except discord.HTTPException as e:
            logger.error(f"❌ Discord API 오류: {e.status} {e.text}")
            return None
        except Exception as e:
            logger.error(f"❌ 예상치 못한 오류: {e}", exc_info=True)
            return None

    async def set_channel_permissions(
        self,
        channel: discord.TextChannel,
        role: discord.Role,
        **permissions: bool
    ) -> bool:
        """
        채널에 대한 역할의 권한 설정

        Args:
            channel: 대상 채널
            role: 권한을 설정할 역할
            **permissions: 권한 설정 (read_messages=True 등)

        Returns:
            성공 여부
        """
        try:
            await channel.set_permissions(role, **permissions)
            logger.info(f"✅ 권한 설정 완료: {channel.name} - {role.name}")
            return True

        except discord.Forbidden:
            logger.error(f"❌ 권한 부족: 채널 권한을 설정할 수 없습니다")
            return False
        except Exception as e:
            logger.error(f"❌ 권한 설정 오류: {e}", exc_info=True)
            return False

    async def send_embed_message(
        self,
        channel: discord.TextChannel,
        title: str,
        description: str,
        color: discord.Color,
        **embed_kwargs
    ) -> bool:
        """
        채널에 Embed 메시지 전송

        Args:
            channel: 메시지를 보낼 채널
            title: 임베드 제목
            description: 임베드 설명
            color: 임베드 색상
            **embed_kwargs: 추가 Embed 설정

        Returns:
            성공 여부
        """
        try:
            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                **embed_kwargs
            )
            await channel.send(embed=embed)
            logger.info(f"✅ 메시지 전송 완료: {channel.name}")
            return True

        except discord.Forbidden:
            logger.error(f"❌ 권한 부족: 메시지를 보낼 수 없습니다")
            return False
        except discord.HTTPException as e:
            logger.error(f"❌ Discord API 오류: {e.status} {e.text}")
            return False
        except Exception as e:
            logger.error(f"❌ 메시지 전송 오류: {e}", exc_info=True)
            return False

    async def reorder_channels_in_category(
        self,
        category: discord.CategoryChannel,
        template_keys: list[str]
    ) -> bool:
        """
        카테고리 내 채널들의 순서를 정렬

        Args:
            category: 대상 카테고리
            template_keys: 원하는 채널 순서 (채널 이름 리스트)

        Returns:
            성공 여부
        """
        try:
            for correct_index, ch_name in enumerate(template_keys):
                channel = discord.utils.get(
                    category.text_channels,
                    name=ch_name
                )
                if channel and channel.position != correct_index:
                    await channel.edit(position=correct_index)
                    logger.debug(f"채널 위치 조정: {ch_name} → {correct_index}")

            await asyncio.sleep(CHANNEL_OPERATION_DELAY)
            logger.info(f"✅ 채널 순서 정렬 완료: {category.name}")
            return True

        except discord.Forbidden:
            logger.error(f"❌ 권한 부족: 채널 순서를 변경할 수 없습니다")
            return False
        except Exception as e:
            logger.error(f"❌ 채널 순서 정렬 오류: {e}", exc_info=True)
            return False

    async def delete_channels_in_category(
        self,
        category: discord.CategoryChannel
    ) -> int:
        """
        카테고리 내 모든 채널 삭제

        Args:
            category: 대상 카테고리

        Returns:
            삭제된 채널의 개수
        """
        count = 0
        logger.info(f"카테고리 내 채널 삭제 시작: {category.name}")

        # 채널 리스트를 복사 (순회 중 변경 방지)
        channels = list(category.text_channels)

        for channel in channels:
            try:
                await channel.delete()
                logger.info(f"✅ 채널 삭제: {channel.name}")
                count += 1
                await asyncio.sleep(CHANNEL_OPERATION_DELAY)

            except discord.Forbidden:
                logger.error(f"❌ 권한 부족: {channel.name}을 삭제할 수 없습니다")
            except Exception as e:
                logger.error(f"❌ 채널 삭제 오류 ({channel.name}): {e}")

        logger.info(f"카테고리 내 채널 삭제 완료: {count}개 삭제됨")
        return count
