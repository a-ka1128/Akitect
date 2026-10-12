"""방 보관본 생성"""
import asyncio
import zipfile
from datetime import datetime, timezone
from types import SimpleNamespace

import config
from utils.archiver import Archiver


class FakeAttachment:
    def __init__(self, filename, size, content_type="application/octet-stream"):
        self.filename = filename
        self.size = size
        self.content_type = content_type
        self.read_called = False

    async def read(self):
        self.read_called = True
        return b"x" * self.size


class FakeChannel:
    def __init__(self, name, messages):
        self.name = name
        self._messages = messages

    async def history(self, limit=None, oldest_first=True):
        for m in self._messages:
            yield m


def make_message(content, attachments=()):
    return SimpleNamespace(
        content=content,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        author=SimpleNamespace(display_name="<b>민수</b>"),
        embeds=[],
        attachments=list(attachments),
    )


def test_archive_streams_to_disk_and_skips_big_files(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ARCHIVE_DIR", tmp_path / "archives")
    monkeypatch.setattr(config, "ARCHIVE_MAX_ATTACHMENT_BYTES", 1000)
    monkeypatch.setattr(config, "ARCHIVE_MAX_TOTAL_BYTES", 1500)

    small = FakeAttachment("a.txt", 800)
    too_big = FakeAttachment("big.bin", 5000)       # 1개 상한 초과
    over_total = FakeAttachment("b.txt", 800)       # 총량 상한 초과 (800 + 800 > 1500)
    channel = FakeChannel("상담", [
        make_message("<script>alert(1)</script>", [small, too_big]),
        make_message("두번째", [over_total]),
    ])
    category = SimpleNamespace(name="민수", text_channels=[channel])

    stats = asyncio.run(Archiver.archive(category, None))

    assert stats["saved"] == "disk"
    assert stats["messages"] == 2
    assert stats["attachments"] == 1
    assert stats["skipped"] == 2
    assert not too_big.read_called and not over_total.read_called

    with zipfile.ZipFile(stats["path"]) as z:
        names = z.namelist()
        assert "transcript.html" in names
        assert any(n.endswith("a.txt") for n in names)
        html_doc = z.read("transcript.html").decode("utf-8")

    # 메시지·작성자 이름은 HTML 이스케이프된다
    assert "<script>" not in html_doc and "&lt;script&gt;" in html_doc
    assert "<b>민수</b>" not in html_doc
    assert "용량 제한으로 미포함" in html_doc

    # 임시 파일이 남지 않는다
    assert list((tmp_path / "archives" / ".tmp").iterdir()) == []
