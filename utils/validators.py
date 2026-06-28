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
        - 공백 불가 (Discord가 채널명의 공백을 자동 변환하므로 미리 막는다)

        Args:
            name: 검증할 채널 이름

        Returns:
            (성공 여부, 에러 메시지)
        """
        if not name or not name.strip():
            return False, "채널 이름은 비울 수 없습니다."

        if len(name) < 2:
            return False, "채널 이름은 2자 이상이어야 합니다."

        if len(name) > 100:
            return False, "채널 이름은 100자 이하여야 합니다."

        if ' ' in name:
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
    def validate_url(url: str) -> Tuple[bool, str]:
        """
        링크 버튼용 URL 검증

        규칙: http:// 또는 https:// 로 시작, 512자 이하 (Discord 버튼 URL 제한)

        Args:
            url: 검증할 URL

        Returns:
            (성공 여부, 에러 메시지)
        """
        if not url or not url.strip():
            return False, "URL은 비울 수 없습니다."

        if not (url.startswith("http://") or url.startswith("https://")):
            return False, "URL은 http:// 또는 https:// 로 시작해야 합니다."

        if len(url) > 512:
            return False, "URL은 512자 이하여야 합니다."

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