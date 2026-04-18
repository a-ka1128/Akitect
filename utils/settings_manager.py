"""
설정 파일(settings.json) 관리
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    settings.json 파일을 관리하는 클래스

    길드별 채널 템플릿, 역할 설정 등을 저장/로드합니다.
    """

    def __init__(self, file_path: str | Path = "settings.json"):
        """
        Settings Manager 초기화

        Args:
            file_path: settings.json 파일 경로
        """
        self.path = Path(file_path)
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """
        settings.json 파일 로드

        Returns:
            파일 내용 (딕셔너리), 파일이 없거나 오류면 빈 딕셔너리
        """
        if self.path.exists():
            try:
                content = self.path.read_text(encoding="utf-8")
                data = json.loads(content)
                logger.info(f"✅ 설정 파일 로드 완료: {self.path}")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON 파싱 오류: {e}")
                return {}
            except Exception as e:
                logger.error(f"❌ 파일 로드 오류: {e}")
                return {}

        logger.warning(f"⚠️ 설정 파일을 찾을 수 없습니다: {self.path}")
        return {}

    def save(self) -> bool:
        """
        현재 데이터를 settings.json으로 저장

        Returns:
            저장 성공 여부
        """
        try:
            self.path.write_text(
                json.dumps(self.data, indent=4, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.info("💾 설정 파일 저장 완료")
            return True
        except IOError as e:
            logger.error(f"❌ 설정 파일 저장 실패: {e}")
            return False

    def _ensure_guild(self, guild_id: str):
        """
        길드 데이터가 존재하는지 확인하고, 없으면 생성

        Args:
            guild_id: 길드 ID (문자열)
        """
        if guild_id not in self.data:
            self.data[guild_id] = {}

    # ================================================================
    # 채널 템플릿 관련 메서드
    # ================================================================

    def get_channels(self, guild_id: str) -> Dict[str, Dict]:
        """
        특정 길드의 모든 채널 템플릿 조회

        Args:
            guild_id: 길드 ID (문자열)

        Returns:
            채널 템플릿 딕셔너리 (없으면 빈 딕셔너리)
        """
        self._ensure_guild(guild_id)
        return self.data[guild_id].get("channels", {})

    def get_channel(self, guild_id: str, channel_name: str) -> Optional[Dict]:
        """
        특정 채널 템플릿 조회

        Args:
            guild_id: 길드 ID
            channel_name: 채널 이름

        Returns:
            채널 정보 딕셔너리 또는 None
        """
        channels = self.get_channels(guild_id)
        return channels.get(channel_name)

    def set_channel(self, guild_id: str, ch_name: str, info: Dict[str, Any]) -> bool:
        """
        채널 템플릿 저장 또는 업데이트

        Args:
            guild_id: 길드 ID
            ch_name: 채널 이름
            info: 채널 정보 (msg, role_ids 등)

        Returns:
            성공 여부
        """
        try:
            self._ensure_guild(guild_id)
            if "channels" not in self.data[guild_id]:
                self.data[guild_id]["channels"] = {}

            self.data[guild_id]["channels"][ch_name] = info
            self.save()
            logger.info(f"✅ 채널 템플릿 저장: {guild_id} - {ch_name}")
            return True
        except Exception as e:
            logger.error(f"❌ 채널 템플릿 저장 오류: {e}")
            return False

    def add_role_to_channel(self, guild_id: str, ch_name: str, role_id: int) -> bool:
        """
        채널 템플릿에 역할 추가

        Args:
            guild_id: 길드 ID
            ch_name: 채널 이름
            role_id: 추가할 역할 ID

        Returns:
            성공 여부
        """
        try:
            channels = self.get_channels(guild_id)
            if ch_name not in channels:
                logger.warning(f"⚠️ 채널을 찾을 수 없습니다: {ch_name}")
                return False

            # role_ids 리스트 초기화 (기존 role_id 호환성)
            if "role_ids" not in channels[ch_name]:
                channels[ch_name]["role_ids"] = []
                # 기존 role_id가 있으면 role_ids로 이전
                if "role_id" in channels[ch_name]:
                    channels[ch_name]["role_ids"].append(channels[ch_name]["role_id"])
                    del channels[ch_name]["role_id"]

            if role_id not in channels[ch_name]["role_ids"]:
                channels[ch_name]["role_ids"].append(role_id)
                self.save()
                logger.info(f"✅ 역할 추가: {ch_name} - {role_id}")
                return True

            logger.warning(f"⚠️ 이미 추가된 역할입니다: {role_id}")
            return False
        except Exception as e:
            logger.error(f"❌ 역할 추가 오류: {e}")
            return False

    def remove_role_from_channel(self, guild_id: str, ch_name: str, role_id: int) -> bool:
        """
        채널 템플릿에서 역할 제거

        Args:
            guild_id: 길드 ID
            ch_name: 채널 이름
            role_id: 제거할 역할 ID

        Returns:
            성공 여부
        """
        try:
            channels = self.get_channels(guild_id)
            if ch_name not in channels:
                logger.warning(f"⚠️ 채널을 찾을 수 없습니다: {ch_name}")
                return False

            if "role_ids" not in channels[ch_name]:
                logger.warning(f"⚠️ 역할이 설정되지 않았습니다: {ch_name}")
                return False

            if role_id in channels[ch_name]["role_ids"]:
                channels[ch_name]["role_ids"].remove(role_id)
                self.save()
                logger.info(f"✅ 역할 제거: {ch_name} - {role_id}")
                return True

            logger.warning(f"⚠️ 해당 역할을 찾을 수 없습니다: {role_id}")
            return False
        except Exception as e:
            logger.error(f"❌ 역할 제거 오류: {e}")
            return False

    def rename_channel(self, guild_id: str, old_name: str, new_name: str) -> bool:
        """
        채널 템플릿 이름 변경

        Args:
            guild_id: 길드 ID
            old_name: 기존 채널 이름
            new_name: 새 채널 이름

        Returns:
            성공 여부
        """
        try:
            channels = self.get_channels(guild_id)
            if old_name not in channels:
                logger.warning(f"⚠️ 채널을 찾을 수 없습니다: {old_name}")
                return False

            channels[new_name] = channels.pop(old_name)
            self.save()
            logger.info(f"✅ 채널 이름 변경: {old_name} → {new_name}")
            return True
        except Exception as e:
            logger.error(f"❌ 채널 이름 변경 오류: {e}")
            return False

    def delete_channel(self, guild_id: str, ch_name: str) -> bool:
        """
        채널 템플릿 삭제

        Args:
            guild_id: 길드 ID
            ch_name: 채널 이름

        Returns:
            성공 여부
        """
        try:
            channels = self.get_channels(guild_id)
            if ch_name not in channels:
                logger.warning(f"⚠️ 채널을 찾을 수 없습니다: {ch_name}")
                return False

            del channels[ch_name]
            self.save()
            logger.info(f"🗑️ 채널 템플릿 삭제: {ch_name}")
            return True
        except Exception as e:
            logger.error(f"❌ 채널 삭제 오류: {e}")
            return False

    # ================================================================
    # 역할 설정 관련 메서드
    # ================================================================

    def get_auto_role(self, guild_id: str) -> Optional[int]:
        """
        길드의 자동 할당 역할 ID 조회

        Args:
            guild_id: 길드 ID

        Returns:
            역할 ID 또는 None
        """
        self._ensure_guild(guild_id)
        return self.data[guild_id].get("auto_role")

    def set_auto_role(self, guild_id: str, role_id: int) -> bool:
        """
        길드의 자동 할당 역할 설정

        Args:
            guild_id: 길드 ID
            role_id: 역할 ID

        Returns:
            성공 여부
        """
        try:
            self._ensure_guild(guild_id)
            self.data[guild_id]["auto_role"] = role_id
            self.save()
            logger.info(f"✅ 자동 역할 설정: {role_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 자동 역할 설정 오류: {e}")
            return False

    def get_support_role(self, guild_id: str) -> Optional[int]:
        """
        길드의 지원 역할 ID 조회

        Args:
            guild_id: 길드 ID

        Returns:
            역할 ID 또는 None
        """
        self._ensure_guild(guild_id)
        return self.data[guild_id].get("support_role")

    def set_support_role(self, guild_id: str, role_id: int) -> bool:
        """
        길드의 지원 역할 설정

        Args:
            guild_id: 길드 ID
            role_id: 역할 ID

        Returns:
            성공 여부
        """
        try:
            self._ensure_guild(guild_id)
            self.data[guild_id]["support_role"] = role_id
            self.save()
            logger.info(f"✅ 지원 역할 설정: {role_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 지원 역할 설정 오류: {e}")
            return False
