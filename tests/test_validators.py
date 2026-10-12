"""입력값 검증"""
from utils.validators import Validators
from utils.channel_manager import ChannelManager
from types import SimpleNamespace


def test_normalize_channel_name():
    assert Validators.normalize_channel_name(" FAQ ") == "faq"
    assert Validators.normalize_channel_name("상담 안내") == "상담-안내"


def test_validate_channel_name():
    assert Validators.validate_channel_name("공지")[0]
    assert not Validators.validate_channel_name("a")[0]
    assert not Validators.validate_channel_name("a b")[0]


def test_validate_url():
    assert Validators.validate_url("https://example.com")[0]
    assert not Validators.validate_url("javascript:alert(1)")[0]


def test_find_text_channel_matches_discord_lowercase():
    # 디스코드는 'FAQ' 템플릿으로 만든 채널을 'faq' 로 저장한다
    faq = SimpleNamespace(name="faq")
    category = SimpleNamespace(text_channels=[SimpleNamespace(name="공지"), faq])
    assert ChannelManager.find_text_channel(category, "FAQ") is faq
    assert ChannelManager.find_text_channel(category, "없음") is None


def test_template_role_ids_legacy_and_new():
    assert ChannelManager.template_role_ids({"role_id": 1}) == [1]
    assert ChannelManager.template_role_ids({"role_ids": [2, 3], "role_id": 1}) == [2, 3]
    assert ChannelManager.template_role_ids({}) == []
