"""
Discord 카테고리(카테고리=방) 관리
"""
import asyncio
import logging
from typing import Optional, Dict, Any

import discord
from config import CHANNEL_OPERATION_DELAY

logger = logging.getLogger(__name__)

# 길드별 정렬 잠금 — 여러 명이 동시에 입장해도 정렬이 겹쳐 실행되지 않게 한다
_sort_locks: Dict[int, asyncio.Lock] = {}


def room_sort_key(name: str) -> tuple[int, str]:
    """
    방 이름 정렬 키: 숫자 → 영문(abc, 대소문자 무시) → 한글(가나다) → 기타(이모지 등)
    """
    lowered = name.casefold()
    first = lowered[:1]
    if first and first in "0123456789":
        group = 0
    elif "a" <= first <= "z":
        group = 1
    elif "가" <= first <= "힣" or "ㄱ" <= first <= "ㆎ":
        group = 2
    else:
        group = 3
    return group, lowered


def is_member_room(category: discord.CategoryChannel) -> bool:
    """
    멤버 방인지 판별

    봇이 만든 방은 멤버 개인에게 보기 권한을 준다. 역할로만 권한을 거는
    공지/관리용 고정 카테고리와 이 점으로 구분한다.
    (퇴장해서 캐시에 없는 멤버는 discord.Object 로 들어오므로 Role 이 아니면 멤버로 본다)
    """
    me_id = category.guild.me.id
    for target, overwrite in category.overwrites.items():
        if isinstance(target, discord.Role) or target.id == me_id:
            continue
        if overwrite.read_messages:
            return True
    return False


def room_name_for(display_name: str, username: str, taken: set[str]) -> str:
    """
    겹치지 않는 방 이름 고르기

    같은 이름의 카테고리가 이미 있으면 '이름 (아이디)' → '이름 (2)' 순으로 붙인다.
    (기존 방에 합류시키면 같은 이름으로 들어온 사람이 남의 방을 볼 수 있으므로 항상 새 방을 만든다)

    Args:
        display_name: 멤버 표시 이름
        username: 멤버 고유 아이디 (member.name)
        taken: 이미 쓰는 카테고리 이름들 (casefold 된 값)
    """
    candidates = [display_name]
    if username.casefold() != display_name.casefold():
        candidates.append(f"{display_name} ({username})")
    for name in candidates:
        if name.casefold() not in taken:
            return name[:100]
    n = 2
    while f"{display_name} ({n})".casefold() in taken:
        n += 1
    return f"{display_name} ({n})"[:100]


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
        logger.debug(f"CategoryManager 초기화: {guild.name}")

    def find_category_by_name(self, name: str) -> Optional[discord.CategoryChannel]:
        """
        이름으로 카테고리 찾기

        정확한 이름 일치(대소문자 무시)로만 찾습니다.

        Args:
            name: 찾을 카테고리 이름

        Returns:
            찾은 카테고리, 또는 None
        """
        # 정확한 이름 찾기
        category = discord.utils.get(self.guild.categories, name=name)
        if category:
            return category

        # 대소문자 무시 정확 일치
        # (부분 일치는 'u3'가 'u32 (새계정)'에 잘못 매칭되는 오배정 위험이 있어 사용하지 않는다)
        lowered = name.lower()
        for cat in self.guild.categories:
            if cat.name and cat.name.lower() == lowered:
                return cat

        return None

    def find_member_room(
        self,
        member: discord.Member,
        room_id: Optional[int] = None
    ) -> Optional[discord.CategoryChannel]:
        """
        멤버 '본인'의 방(카테고리) 찾기

        1) 소유자 기록(room_id)이 있으면 ID로 찾는다.
        2) 기록이 없는 예전 방은 이름(정확 일치) + 본인 접근 권한을 둘 다 만족해야 한다.
        퇴장 자동 삭제처럼 되돌릴 수 없는 작업에서 엉뚱한 방을 지우지 않도록
        보수적으로 판별한다. (닉네임을 바꾼 경우엔 못 찾을 수 있음 → 이때는 자동 정리 생략)

        Args:
            member: 대상 멤버
            room_id: settings 에 기록된 본인 방 카테고리 ID

        Returns:
            본인 방 카테고리, 또는 None
        """
        if room_id:
            category = self.guild.get_channel(room_id)
            if isinstance(category, discord.CategoryChannel):
                return category

        lowered = member.display_name.lower()
        for category in self.guild.categories:
            if category.name and category.name.lower() == lowered:
                if category.overwrites_for(member).read_messages:
                    return category
        return None

    def is_member_room(self, category: discord.CategoryChannel) -> bool:
        """멤버 방인지 판별 (모듈 함수 is_member_room 참고)"""
        return is_member_room(category)

    def member_rooms(self) -> list[discord.CategoryChannel]:
        """서버의 멤버 방 카테고리 목록 (화면 순서)"""
        return [c for c in self.guild.categories if is_member_room(c)]

    def unique_room_name(self, member: discord.Member) -> str:
        """다른 카테고리와 겹치지 않는 새 방 이름"""
        taken = {c.name.casefold() for c in self.guild.categories}
        return room_name_for(member.display_name, member.name, taken)

    def other_room_members(
        self,
        category: discord.CategoryChannel,
        member: discord.abc.Snowflake
    ) -> list[discord.Member]:
        """
        방을 함께 쓰는 '서버에 남아 있는' 다른 멤버들

        관리자가 /방생성 으로 부계정 등을 기존 방에 넣은 경우,
        한 명이 나갔다고 방 전체를 지우지 않기 위해 쓴다.
        (서버를 떠난 멤버는 캐시에 없어 discord.Object 로 들어오므로 제외된다)
        """
        return [
            target for target, overwrite in category.overwrites.items()
            if isinstance(target, discord.Member)
            and target.id not in (member.id, self.guild.me.id)
            and not target.bot
            and overwrite.read_messages
        ]

    async def sort_rooms(self) -> int:
        """
        멤버 방(카테고리)을 이름순으로 정렬

        고정 카테고리는 제자리에 두고, 멤버 방이 차지하던 자리 안에서만 순서를 바꾼다.
        API 한 번(일괄 위치 변경)으로 처리하므로 방이 많아도 빠르다.

        Returns:
            자리가 바뀐 방 개수 (실패 시 -1)
        """
        lock = _sort_locks.setdefault(self.guild.id, asyncio.Lock())
        async with lock:
            current = self.guild.categories  # 화면 표시 순서 (위→아래)
            room_ids = {c.id for c in current if self.is_member_room(c)}
            if len(room_ids) < 2:
                return 0

            sorted_rooms = iter(sorted(
                (c for c in current if c.id in room_ids),
                key=lambda c: room_sort_key(c.name)
            ))
            new_order = [next(sorted_rooms) if c.id in room_ids else c for c in current]

            moved = sum(1 for old, new in zip(current, new_order) if old.id != new.id)
            if moved == 0:
                return 0

            payload = [{"id": c.id, "position": i} for i, c in enumerate(new_order)]
            try:
                # discord.py 2.3 에는 일괄 위치 변경 공개 API가 없어 내부 http 를 쓴다.
                # (channel.edit(position=) 을 방마다 부르면 방 수만큼 API 호출 + 레이트리밋)
                await self.guild._state.http.bulk_channel_update(
                    self.guild.id, payload, reason="방 이름순 정렬"
                )
                logger.info(f"✅ 방 이름순 정렬: {moved}개 이동 (방 {len(room_ids)}개)")
                return moved
            except discord.Forbidden:
                logger.error("❌ 권한 부족: 카테고리 순서를 변경할 수 없습니다 (채널 관리 권한 필요)")
                return -1
            except discord.HTTPException as e:
                logger.error(f"❌ 방 정렬 API 오류: {e.status} {e.text}")
                return -1
            except Exception as e:
                # 정렬 실패가 방 생성 결과를 '오류'로 뒤집지 않도록 여기서 흡수한다
                logger.error(f"❌ 방 정렬 오류: {e}", exc_info=True)
                return -1

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
        # 같은 이름의 기존 카테고리를 돌려주지 않는다.
        # (호출자가 그 방을 새 멤버 것으로 착각해 소유자 기록·삭제가 꼬일 수 있음)
        # 이름 중복은 호출 전에 unique_room_name / find_category_by_name 으로 처리한다.
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
