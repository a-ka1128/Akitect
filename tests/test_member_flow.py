"""
입장·퇴장 흐름 — 같은 이름으로 들어온 사람이 남의 방을 차지/삭제하지 못하는지

discord 객체는 spec 을 건 MagicMock 으로 흉내 낸다 (async 메서드는 자동으로 AsyncMock).
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import main
from utils import SettingsManager


def make_member(member_id, name, display_name, guild):
    m = MagicMock(spec=discord.Member)
    m.id, m.name, m.display_name = member_id, name, display_name
    m.bot, m.pending, m.guild = False, False, guild
    m.mention = f"<@{member_id}>"
    return m


def make_category(category_id, name, guild, overwrites):
    c = MagicMock(spec=discord.CategoryChannel)
    c.id, c.name, c.guild = category_id, name, guild
    c.overwrites = overwrites
    c.overwrites_for.side_effect = lambda obj: next(
        (ow for t, ow in overwrites.items() if t.id == obj.id), discord.PermissionOverwrite()
    )
    c.text_channels, c.channels = [], []
    return c


@pytest.fixture
def env(tmp_path, monkeypatch):
    guild = MagicMock(spec=discord.Guild)
    guild.id, guild.name = 1, "테스트서버"
    guild.me = MagicMock(spec=discord.Member, id=999)
    guild.filesize_limit = 10 * 1024 * 1024
    guild.get_role.return_value = None

    victim = make_member(10, "victim", "민수", guild)
    victim_room = make_category(
        100, "민수", guild, {victim: discord.PermissionOverwrite(read_messages=True)}
    )
    guild.categories = [victim_room]
    guild.channels = [victim_room]
    guild.get_channel.side_effect = lambda cid: next(
        (c for c in guild.categories if c.id == cid), None
    )

    created = []

    async def create_category(name, overwrites=None, **_):
        cat = make_category(200 + len(created), name, guild, overwrites)
        created.append(cat)
        guild.categories.append(cat)
        return cat

    guild.create_category.side_effect = create_category

    settings = SettingsManager(tmp_path / "settings.json")
    settings.set_channel("1", "상담", {"msg": "안내"})
    settings.register_room("1", victim_room.id, victim.id)
    monkeypatch.setattr(main, "settings_manager", settings)
    monkeypatch.setattr(main.config, "CHANNEL_OPERATION_DELAY", 0)

    archive = AsyncMock(return_value={"messages": 0, "attachments": 0, "saved": "disk"})
    monkeypatch.setattr(main.Archiver, "archive", archive)

    return SimpleNamespace(
        guild=guild, victim=victim, victim_room=victim_room,
        created=created, settings=settings, archive=archive,
    )


def test_same_name_joiner_gets_own_room(env):
    attacker = make_member(20, "attacker", "민수", env.guild)

    asyncio.run(main.handle_new_member(attacker))

    # 피해자 방에는 권한이 추가되지 않는다
    env.victim_room.set_permissions.assert_not_called()
    # 겹치지 않는 이름으로 새 방이 생기고, 소유자로 기록된다
    assert [c.name for c in env.created] == ["민수 (attacker)"]
    assert env.settings.get_room_of("1", attacker.id) == env.created[0].id


def test_same_name_leaver_does_not_delete_victim_room(env):
    attacker = make_member(20, "attacker", "민수", env.guild)
    asyncio.run(main.handle_new_member(attacker))
    attacker_room = env.created[0]

    asyncio.run(main.on_member_remove(attacker))

    # 공격자 본인 방만 보관·삭제된다
    env.archive.assert_awaited_once()
    assert env.archive.await_args.args[0] is attacker_room
    attacker_room.delete.assert_awaited_once()
    env.victim_room.delete.assert_not_called()


def test_shared_room_is_kept_when_one_member_leaves(env):
    alt = make_member(30, "victim_alt", "민수2", env.guild)
    env.victim_room.overwrites[alt] = discord.PermissionOverwrite(read_messages=True)

    asyncio.run(main.on_member_remove(env.victim))

    env.archive.assert_not_called()
    env.victim_room.delete.assert_not_called()
    assert env.settings.get_room_of("1", alt.id) == env.victim_room.id


def test_pending_member_waits_for_screening(env, monkeypatch):
    handler = AsyncMock()
    monkeypatch.setattr(main, "handle_new_member", handler)
    newbie = make_member(40, "newbie", "새내기", env.guild)
    newbie.pending = True

    asyncio.run(main.on_member_join(newbie))
    handler.assert_not_called()

    after = make_member(40, "newbie", "새내기", env.guild)
    asyncio.run(main.on_member_update(newbie, after))
    handler.assert_awaited_once_with(after)
