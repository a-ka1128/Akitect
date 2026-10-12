"""
멤버 방(카테고리 + 템플릿 채널) 생성

입장 시 자동 생성과 /방생성 이 같은 경로를 쓰도록 한 곳에 모았다.
"""
import asyncio
import logging

import discord

import config
from .settings_manager import SettingsManager
from .channel_manager import ChannelManager
from .category_manager import CategoryManager

logger = logging.getLogger(__name__)


async def build_member_room(
    guild: discord.Guild,
    member: discord.Member,
    settings: SettingsManager
) -> tuple[bool, str]:
    """
    멤버 전용 새 방을 만들고 템플릿 채널·안내문·역할 권한을 채운다.

    같은 이름의 카테고리가 있어도 합류시키지 않고 겹치지 않는 이름으로 새로 만든다.
    (기존 방 합류는 관리자가 /방생성 으로 명시적으로 할 때만)

    Returns:
        (성공 여부, 메시지)
    """
    guild_id = str(guild.id)
    channels = settings.get_channels(guild_id)
    if not channels:
        logger.warning(f"⚠️ 템플릿이 없습니다: {guild.name}")
        return False, "설정된 채널 템플릿이 없습니다."

    # 서버 채널 한도를 넘으면 방이 반쯤만 만들어지므로 미리 막는다
    needed = len(channels) + 1  # 카테고리 1 + 채널 N
    if len(guild.channels) + needed > config.GUILD_CHANNEL_LIMIT:
        logger.error(
            f"❌ 채널 한도 초과 우려로 방 생성 중단: {member.name} "
            f"(현재 {len(guild.channels)}개 + 필요 {needed}개 > {config.GUILD_CHANNEL_LIMIT})"
        )
        return False, f"서버 채널 수가 한도({config.GUILD_CHANNEL_LIMIT}개)에 가까워 방을 만들 수 없습니다."

    category_manager = CategoryManager(guild)
    name = category_manager.unique_room_name(member)
    logger.info(f"새로운 카테고리 생성 시작: {name}")

    new_category = await category_manager.create_category(name, member)
    if not new_category:
        return False, "카테고리 생성에 실패했습니다."

    settings.register_room(guild_id, new_category.id, member.id)
    logger.info(f"✅ 카테고리 생성: {new_category.name}")

    channel_manager = ChannelManager(guild)
    for i, (ch_name, ch_info) in enumerate(channels.items()):
        try:
            new_channel = await channel_manager.create_in_category(
                new_category,
                ch_name,
                position=i
            )
            if not new_channel:
                logger.warning(f"⚠️ 채널 생성 실패: {ch_name}")
                continue

            # 안내문과 파일 전송 (파일이 커도 안내문은 항상 게시되도록 분리 전송)
            await channel_manager.send_template_content(
                new_channel,
                ch_info,
                title=ch_name,
                content=member.mention if i == 0 else None,  # 첫 채널만 멤버 태그
                thumbnail_url=member.display_avatar.url,
            )
            await channel_manager.apply_template_roles(new_channel, ch_info)
            await asyncio.sleep(config.CHANNEL_OPERATION_DELAY)

        except Exception as e:
            logger.error(f"❌ 채널 '{ch_name}' 생성 중 오류: {e}", exc_info=True)

    await channel_manager.reorder_channels_in_category(new_category, list(channels.keys()))

    # 새 방을 이름순 자리로 (실패해도 방 생성은 성공으로 처리)
    await category_manager.sort_rooms()

    logger.info(f"✅ 방 생성 완료: {new_category.name}")
    return True, f"새로운 카테고리 '{new_category.name}'가 생성되었습니다."
