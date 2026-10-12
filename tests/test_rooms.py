"""방 이름·정렬 규칙"""
from utils.category_manager import room_name_for, room_sort_key


def test_room_name_unused_keeps_display_name():
    assert room_name_for("민수", "minsu01", set()) == "민수"


def test_room_name_taken_adds_username():
    # 같은 이름의 방(또는 고정 카테고리)이 있으면 절대 그 방을 재사용하지 않는다
    assert room_name_for("민수", "minsu01", {"민수"}) == "민수 (minsu01)"


def test_room_name_is_case_insensitive():
    assert room_name_for("Admin", "evil", {"admin"}) == "Admin (evil)"


def test_room_name_falls_back_to_number():
    taken = {"minsu", "minsu (2)"}
    assert room_name_for("minsu", "minsu", taken) == "minsu (3)"


def test_room_name_max_length():
    assert len(room_name_for("a" * 32, "b" * 32, {"a" * 32})) <= 100


def test_room_sort_key_order():
    names = ["가나", "abc", "1번", "Zed", "😀"]
    assert sorted(names, key=room_sort_key) == ["1번", "abc", "Zed", "가나", "😀"]
