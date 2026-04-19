"""
입력값 검증 유틸리티
"""
from typing import Tuple


class Validators:
    """입력값 검증을 위한 유틸리티 클래스"""

    @staticmethod
    def validate_channel_name(name: str) -> Tuple[bool, str]:
        """
        Discord 채널 이름 검증

        규칙:
        - 비어있지 않음
        - 2-100 글자
        - 알파벳, 숫자, -, _ 만 사용

        Args:
            name: 검증할 채널 이름

        Returns:
            (성공 여부, 에러 메시지)
        """
        if not name:
            return False, "채널 이름은 비울 수 없습니다."

        if len(name) < 2:
            return False, "채널 이름은 2자 이상이어야 합니다."

        if len(name) > 100:
            return False, "채널 이름은 100자 이하여야 합니다."

        # 알파벳, 숫자, -, _ 만 허용
        if not name or ' ' in name:
            return False, "채널 이름에는 공백을 사용할 수 없습니다."

        return True, ""

    @staticmethod
    def validate_message(msg: str) -> Tuple[bool, str]:
        """
        메시지 내용 검증

        규칙:
        - 비어있지 않음
        - 4000 글자 이하 (Discord 임베드 한계)

        Args:
            msg: 검증할 메시지

        Returns:
            (성공 여부, 에러 메시지)
        """
        if not msg or not msg.strip():
            return False, "메시지는 비울 수 없습니다."

        if len(msg) > 4000:
            return False, "메시지는 4000자 이하여야 합니다."

        return True, ""

    @staticmethod
    def validate_order(order: int, max_order: int) -> Tuple[bool, str, int]:
        """
        순서 번호 검증

        Args:
            order: 검증할 순서 번호
            max_order: 최대 순서 번호

        Returns:
            (성공 여부, 에러 메시지, 보정된 순서 번호)
        """
        if order < 1:
            return False, "순서는 1 이상이어야 합니다.", 1

        if order > max_order:
            return False, f"순서는 {max_order} 이하여야 합니다.", max_order

        return True, "", order

    @staticmethod
    def validate_not_empty(value: str, field_name: str = "값") -> Tuple[bool, str]:
        """
        필드가 비어있지 않은지 검증

        Args:
            value: 검증할 값
            field_name: 필드 이름 (에러 메시지용)

        Returns:
            (성공 여부, 에러 메시지)
        """
        if not value or not value.strip():
            return False, f"{field_name}은(는) 비울 수 없습니다."

        return True, ""
