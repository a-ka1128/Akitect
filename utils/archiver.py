"""
방(카테고리) 대화 보관 (아카이브)

카테고리 안 모든 채널의 메시지를 HTML 트랜스크립트로 만들고,
클라이언트가 올린 첨부파일 원본까지 받아 하나의 ZIP으로 묶는다.
보관 채널이 있으면 거기에 올리고, 너무 크면 VM 디스크에 저장한다.

ZIP은 메모리가 아니라 디스크 임시 파일에 바로 쓰고, 첨부는 개수·총량 상한을 둔다.
(큰 파일을 잔뜩 올린 방을 보관하다 VM 메모리가 바닥나 봇이 죽는 것을 막기 위함)
"""
import os
import re
import html
import uuid
import asyncio
import logging
import tempfile
import zipfile
from pathlib import Path
from datetime import timezone, timedelta

import discord
import config

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


class Archiver:
    """카테고리 대화를 HTML+첨부 ZIP으로 보관하는 유틸리티"""

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    @staticmethod
    async def archive(
        category: discord.CategoryChannel,
        archive_channel: discord.abc.Messageable = None,
    ) -> dict:
        """
        카테고리를 보관한다.

        Args:
            category: 보관할 카테고리
            archive_channel: 보관본을 올릴 채널 (None이면 디스크에만 저장)

        Returns:
            통계 dict {messages, attachments, skipped, channels, saved, path?}
        """
        tmp_path, stats = await Archiver._build_zip(category)
        try:
            return await Archiver._deliver(category, archive_channel, tmp_path, stats)
        finally:
            # 채널 업로드에 성공했거나 오류가 난 경우 남은 임시 파일 정리
            tmp_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------
    @staticmethod
    async def _deliver(
        category: discord.CategoryChannel,
        archive_channel: discord.abc.Messageable,
        tmp_path: Path,
        stats: dict,
    ) -> dict:
        """만든 ZIP을 보관 채널에 올리거나, 못 올리면 디스크에 옮긴다."""
        filename = Archiver._safe_filename(category.name)

        summary = (
            f"📦 **{category.name}** 상담 보관본\n"
            f"채널 {stats['channels']}개 · 메시지 {stats['messages']}개 · 첨부 {stats['attachments']}개"
        )
        if stats["skipped"]:
            summary += f"\n⚠️ 용량 제한으로 첨부 {stats['skipped']}개는 담지 못했습니다"

        # 1) 보관 채널에 업로드 시도 (서버 업로드 한도 이하일 때만)
        if archive_channel is not None:
            size = tmp_path.stat().st_size
            limit = getattr(getattr(archive_channel, "guild", None), "filesize_limit", None)
            if limit is not None and size > limit:
                logger.info(f"보관본이 업로드 한도 초과({size} > {limit} bytes) → 디스크 저장")
            else:
                try:
                    await archive_channel.send(
                        content=summary,
                        file=discord.File(tmp_path, filename=filename),
                    )
                    stats["saved"] = "channel"
                    logger.info(f"✅ 보관본 채널 업로드 완료: {category.name}")
                    return stats
                except discord.HTTPException as e:
                    logger.warning(f"⚠️ 보관본 채널 업로드 실패 → 디스크 저장: {e}")

        # 2) 디스크에 저장 (채널 미설정 또는 용량 초과 폴백)
        path = Archiver._save_to_disk(tmp_path, filename)
        stats["saved"] = "disk"
        stats["path"] = str(path)
        logger.info(f"✅ 보관본 디스크 저장 완료: {path}")

        if archive_channel is not None:
            try:
                await archive_channel.send(
                    f"{summary}\n⚠️ 파일이 커서 서버(VM)에 저장했습니다: `{path}`"
                )
            except discord.HTTPException:
                pass

        return stats

    @staticmethod
    async def _build_zip(category: discord.CategoryChannel) -> tuple[Path, dict]:
        """
        카테고리 대화를 HTML + 첨부파일 ZIP 임시 파일로 만든다.

        Returns:
            (임시 ZIP 경로, 통계 dict) — 임시 파일 정리는 호출자 책임
        """
        tmp_dir = config.ARCHIVE_DIR / ".tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(suffix=".zip", dir=tmp_dir)
        os.close(fd)
        tmp_path = Path(tmp_name)

        try:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as z:
                stats = await Archiver._write_zip(category, z)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise
        return tmp_path, stats

    @staticmethod
    async def _write_zip(category: discord.CategoryChannel, z: zipfile.ZipFile) -> dict:
        """메시지를 읽으며 첨부는 받는 즉시 ZIP에 쓰고, 마지막에 HTML을 쓴다."""
        parts = [Archiver._html_header(category.name)]
        msg_count = 0
        att_count = 0
        att_index = 0
        skipped = 0
        total_bytes = 0

        for channel in category.text_channels:
            parts.append(f'<h2># {html.escape(channel.name)}</h2>')
            try:
                async for m in channel.history(limit=None, oldest_first=True):
                    msg_count += 1
                    ts = m.created_at.astimezone(KST).strftime("%Y-%m-%d %H:%M")
                    author = html.escape(getattr(m.author, "display_name", str(m.author)))
                    content = html.escape(m.content or "").replace("\n", "<br>")

                    block = [f'<div class="msg"><span class="author">{author}</span>'
                             f'<span class="time">{ts}</span>']
                    if content:
                        block.append(f'<div class="content">{content}</div>')

                    # 임베드 (봇 안내문 등)
                    for emb in m.embeds:
                        et = html.escape(emb.title or "")
                        ed = html.escape(emb.description or "").replace("\n", "<br>")
                        block.append(f'<div class="embed"><b>{et}</b><br>{ed}</div>')

                    # 첨부파일 원본 다운로드 (1개·총량 상한을 넘으면 이름만 남김)
                    for att in m.attachments:
                        att_index += 1
                        if (att.size > config.ARCHIVE_MAX_ATTACHMENT_BYTES
                                or total_bytes + att.size > config.ARCHIVE_MAX_TOTAL_BYTES):
                            skipped += 1
                            block.append(
                                f'<div class="att">📎 {html.escape(att.filename)} '
                                f'({att.size / (1024 * 1024):.1f}MB — 용량 제한으로 미포함)</div>'
                            )
                            continue

                        arc = f"attachments/{att_index}_{Archiver._safe_part(att.filename)}"
                        try:
                            data = await att.read()
                            # 첨부는 대부분 이미 압축된 형식이라 무압축으로 저장 (CPU 절약)
                            await asyncio.to_thread(
                                z.writestr, arc, data, compress_type=zipfile.ZIP_STORED
                            )
                            del data
                            total_bytes += att.size
                            att_count += 1
                            if (att.content_type or "").startswith("image"):
                                block.append(
                                    f'<div class="att"><img src="{html.escape(arc)}" '
                                    f'alt="{html.escape(att.filename)}"></div>'
                                )
                            else:
                                block.append(
                                    f'<div class="att">📎 <a href="{html.escape(arc)}">'
                                    f'{html.escape(att.filename)}</a></div>'
                                )
                        except Exception as e:
                            logger.error(f"❌ 첨부 다운로드 실패 ({att.filename}): {e}")
                            block.append(
                                f'<div class="att">📎 {html.escape(att.filename)} (다운로드 실패)</div>'
                            )

                    block.append("</div>")
                    parts.append("".join(block))
            except discord.Forbidden:
                parts.append('<div class="content">(이 채널을 읽을 권한이 없습니다)</div>')

        parts.append("</body></html>")
        z.writestr("transcript.html", "\n".join(parts))

        return {
            "messages": msg_count,
            "attachments": att_count,
            "skipped": skipped,
            "channels": len(category.text_channels),
        }

    @staticmethod
    def _html_header(title: str) -> str:
        safe_title = html.escape(title)
        # CSS는 중괄호가 많아 f-string을 쓰지 않는다.
        css = """
        body { font-family:'Segoe UI',sans-serif; background:#313338; color:#dbdee1;
               padding:20px; max-width:900px; margin:0 auto; }
        h1 { color:#fff; }
        h2 { color:#fff; border-bottom:1px solid #4e5058; padding-bottom:4px; margin-top:32px; }
        .msg { padding:8px 0; }
        .author { font-weight:600; color:#fff; }
        .time { color:#949ba4; font-size:0.75em; margin-left:8px; }
        .content { margin:4px 0; white-space:pre-wrap; word-wrap:break-word; }
        .embed { border-left:4px solid #2ecc71; padding:8px 12px; margin:6px 0;
                 background:#2b2d31; border-radius:4px; }
        .att { margin:6px 0; }
        .att img { max-width:400px; border-radius:6px; display:block; }
        a { color:#00a8fc; }
        """
        return (
            '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
            f"<title>{safe_title} 보관본</title>"
            f"<style>{css}</style></head><body>"
            f"<h1>📋 {safe_title} — 상담 보관본</h1>"
        )

    @staticmethod
    def _safe_part(name: str) -> str:
        """ZIP 내부 파일명으로 안전하게 정리"""
        return re.sub(r"[^\w가-힣.\-]", "_", name)[:80] or "file"

    @staticmethod
    def _safe_filename(name: str) -> str:
        """보관본 ZIP 파일명 (충돌 방지용 짧은 uuid 접미사 포함)"""
        safe = re.sub(r"[^\w가-힣.\-]", "_", name)[:50] or "archive"
        return f"{safe}_{uuid.uuid4().hex[:8]}.zip"

    @staticmethod
    def _save_to_disk(tmp_path: Path, filename: str) -> Path:
        """임시 ZIP을 보관 디렉토리로 옮긴다 (같은 디스크라 복사 없이 이름만 바뀜)"""
        config.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        path = config.ARCHIVE_DIR / filename
        os.replace(tmp_path, path)
        return path
