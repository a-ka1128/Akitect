"""설정 파일 관리"""
import json

from utils.settings_manager import SettingsManager


def test_corrupt_settings_are_backed_up(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ broken", encoding="utf-8")

    sm = SettingsManager(path)
    assert sm.data == {}
    backups = list(tmp_path.glob("settings.json.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{ broken"

    # 이후 저장이 깨진 원본을 덮어쓰지 않는다 (백업이 남아 있음)
    sm.set_auto_role("1", 123)
    assert backups[0].exists()


def test_save_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    sm = SettingsManager(path)
    sm.set_channel("1", "공지", {"msg": "안녕"})
    assert json.loads(path.read_text(encoding="utf-8"))["1"]["channels"]["공지"]["msg"] == "안녕"
    assert SettingsManager(path).get_channel("1", "공지") == {"msg": "안녕"}


def test_room_registry(tmp_path):
    sm = SettingsManager(tmp_path / "settings.json")
    assert sm.get_room_of("1", 42) is None

    sm.register_room("1", 1000, 42)
    assert sm.get_room_of("1", 42) == 1000
    assert sm.get_room_of("2", 42) is None  # 다른 서버와 섞이지 않음

    # 소유자 이전
    sm.register_room("1", 1000, 43)
    assert sm.get_room_of("1", 42) is None
    assert sm.get_room_of("1", 43) == 1000

    assert sm.unregister_room("1", 1000)
    assert sm.get_room_of("1", 43) is None
    assert not sm.unregister_room("1", 1000)


def test_template_files_size(tmp_path):
    sm = SettingsManager(tmp_path / "settings.json")
    sm.set_channel("1", "a", {"msg": "x"})
    sm.set_channel("1", "b", {"msg": "y"})
    sm.add_file_to_channel("1", "a", {"name": "f1", "path": "p1", "size": 100})
    sm.add_file_to_channel("1", "b", {"name": "f2", "path": "p2", "size": 50})
    assert sm.template_files_size("1") == 150
