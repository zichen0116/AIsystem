"""
视频解析器
Gemini 优先，硬失败时回退到旧链路。
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any, Optional

import cv2
import ffmpeg
import imagehash
from PIL import Image

from app.core.config import get_settings
from app.services.ai.asr_service import QwenASRService
from app.services.ai.gemini_multimodal_service import GeminiMultimodalService
from app.services.ai.vision_service import VisionService
from app.services.parsers.base import BaseParser, ParsedChunk, ParseResult

logger = logging.getLogger(__name__)

ASR_SAMPLE_RATE = 16000
PHASH_THRESHOLD = 5
MAX_KEYFRAMES = 15
TIME_BLOCK_SECONDS = 20


class VideoParser(BaseParser):
    def __init__(
        self,
        output_dir: str = "media/extracted",
        interval_seconds: int = 2,
        api_key: Optional[str] = None,
    ):
        settings = get_settings()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.interval_seconds = interval_seconds
        self.api_key = api_key or settings.DASHSCOPE_API_KEY

        if self.api_key:
            self.asr_service = QwenASRService(api_key=self.api_key)
            self.vision_service = VisionService(api_key=self.api_key)
        else:
            self.asr_service = None
            self.vision_service = None

        self.gemini_service = GeminiMultimodalService()
        self.temp_dir = Path("media/temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    @property
    def supported_extensions(self) -> list[str]:
        return [".mp4", ".avi", ".mov", ".mkv", ".flv"]

    async def parse(self, file_path: Path) -> ParseResult:
        if self.gemini_service.is_enabled():
            try:
                return await self._parse_with_gemini(file_path)
            except Exception as exc:
                logger.warning("Gemini video parse failed, fallback to legacy: %s", exc)
                result = await self._parse_with_legacy(file_path)
                return self._apply_fallback_metadata(result, str(exc))

        result = await self._parse_with_legacy(file_path)
        return self._apply_fallback_metadata(result, "missing_google_api_key")

    async def _parse_with_gemini(self, file_path: Path) -> ParseResult:
        file_name = file_path.name
        task_temp_dir = self.temp_dir / f"video_gemini_{uuid.uuid4().hex}"
        task_temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            frame_data = await self._extract_keyframes_only(file_path, file_name, task_temp_dir)
            frame_summaries = await self._build_gemini_frame_summaries(frame_data["frames"])
            audio_chunks = await self._extract_and_transcribe_audio(file_path, file_name, task_temp_dir)
            transcript_text = "\n".join(
                str(chunk.content or "").replace("[音频转录]", "").strip()
                for chunk in audio_chunks
                if str(chunk.content or "").strip()
            ).strip()

            gemini_summary = await self.gemini_service.summarize_video(
                file_name=file_name,
                transcript_text=transcript_text,
                frame_summaries=frame_summaries,
            )
            searchable_text = str(gemini_summary.get("searchable_text") or gemini_summary.get("summary") or "").strip()
            if not searchable_text:
                raise RuntimeError("empty_gemini_video_result")

            chunks: list[ParsedChunk] = [
                ParsedChunk(
                    content=searchable_text,
                    metadata={
                        "source": file_name,
                        "type": "video_summary",
                        "parser_provider": "gemini",
                        "video_summary": str(gemini_summary.get("summary") or searchable_text).strip(),
                        "knowledge_points": list(gemini_summary.get("knowledge_points") or []),
                        "teaching_cases": list(gemini_summary.get("teaching_cases") or []),
                        "time_segments": list(gemini_summary.get("time_segments") or []),
                        "searchable_text": searchable_text,
                        "is_partial": False,
                    },
                )
            ]

            for segment in gemini_summary.get("time_segments") or []:
                if not isinstance(segment, dict):
                    continue
                segment_text = str(segment.get("summary") or segment.get("content") or "").strip()
                if not segment_text:
                    continue
                chunks.append(
                    ParsedChunk(
                        content=segment_text,
                        metadata={
                            "source": file_name,
                            "type": "multimodal_segment",
                            "parser_provider": "gemini",
                            "timestamp": segment.get("timestamp"),
                            "timestamp_label": segment.get("timestamp_label"),
                            "searchable_text": segment_text,
                            "is_partial": False,
                        },
                    )
                )

            return ParseResult(chunks=chunks, images=[frame["path"] for frame in frame_data["frames"]])
        finally:
            await self._cleanup_temp_files(task_temp_dir)

    async def _parse_with_legacy(self, file_path: Path) -> ParseResult:
        chunks: list[ParsedChunk] = []
        images: list[str] = []
        file_name = file_path.name
        task_temp_dir = self.temp_dir / f"video_{uuid.uuid4().hex}"
        task_temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            try:
                frames_result = await self._extract_frames_with_vision(file_path, file_name, task_temp_dir)
                chunks.extend(frames_result["chunks"])
                images.extend(frames_result["images"])
            except Exception as exc:
                logger.error("Visual frame extraction failed: %s", exc)

            audio_chunks: list[ParsedChunk] = []
            try:
                audio_chunks = await self._extract_and_transcribe_audio(file_path, file_name, task_temp_dir)
            except Exception as exc:
                logger.warning("Audio transcription failed but visual parsing continues: %s", exc)

            all_chunks = self._merge_multimodal_chunks(chunks, audio_chunks)
            video_summary = await self._summarize_legacy_video(file_name, all_chunks)
            if video_summary:
                all_chunks.insert(
                    0,
                    ParsedChunk(
                        content=video_summary,
                        metadata={
                            "source": file_name,
                            "type": "video_summary",
                            "parser_provider": "dashscope_summary",
                            "video_summary": video_summary,
                            "is_partial": False,
                        },
                    ),
                )
            return ParseResult(chunks=all_chunks, images=images)
        finally:
            await self._cleanup_temp_files(task_temp_dir)

    async def _summarize_legacy_video(self, file_name: str, chunks: list[ParsedChunk]) -> str:
        source_text = "\n\n".join(str(chunk.content or "").strip() for chunk in chunks if str(chunk.content or "").strip())
        if not source_text:
            return ""

        try:
            from app.services.ai.dashscope_service import get_dashscope_service

            prompt = (
                f"视频文件名：{file_name}\n\n"
                "下面是视频解析得到的 ASR 转写和画面理解材料，可能包含关键帧日志、时间块标记和无意义寒暄。"
                "请不要逐帧描述，不要输出“截图显示/关键帧/时间块”等字样。"
                "请综合整个视频，生成一段 80-160 字的中文视频总结，说明视频主要讲了什么、展示了什么流程、可用于课件的核心信息是什么。\n\n"
                f"{source_text[:6000]}"
            )
            summary = await get_dashscope_service().chat(
                prompt,
                system_prompt="你是教学视频内容总结助手，只输出整体视频总结，不输出逐帧分析。",
                temperature=0.2,
                max_tokens=500,
            )
        except Exception as exc:
            logger.warning("Legacy video summary generation failed: %s", exc)
            return ""

        summary = str(summary or "").strip()
        if not summary or summary.startswith(("错误:", "API 调用失败", "响应格式异常", "请求成功，但响应格式异常")):
            return ""
        return summary

    def _apply_fallback_metadata(self, result: ParseResult, fallback_reason: str) -> ParseResult:
        for chunk in result.chunks:
            metadata = dict(chunk.metadata or {})
            metadata["parser_provider"] = "legacy_fallback"
            metadata["fallback_reason"] = fallback_reason
            metadata.setdefault("is_partial", False)
            chunk.metadata = metadata
        return result

    async def _extract_keyframes_only(self, file_path: Path, file_name: str, task_temp_dir: Path) -> dict[str, Any]:
        frames: list[dict[str, Any]] = []
        loop = asyncio.get_event_loop()
        last_phash: Optional[imagehash.ImageHash] = None

        with ThreadPoolExecutor() as executor:
            cap = await loop.run_in_executor(executor, cv2.VideoCapture, str(file_path))
            if not cap.isOpened():
                raise RuntimeError(f"unable_to_open_video:{file_path}")

            try:
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps <= 0:
                    fps = 1
                frame_interval = max(int(fps * self.interval_seconds), 1)
                frame_count = 0
                keyframe_count = 0

                while True:
                    ret, frame = await loop.run_in_executor(executor, cap.read)
                    if not ret:
                        break

                    if frame_count % frame_interval == 0:
                        timestamp_seconds = frame_count / fps
                        temp_frame_path = task_temp_dir / f"frame_{frame_count}.jpg"
                        cv2.imwrite(str(temp_frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

                        current_phash = await loop.run_in_executor(
                            executor,
                            imagehash.phash,
                            Image.open(str(temp_frame_path)),
                        )
                        should_save = last_phash is None or (current_phash - last_phash) > PHASH_THRESHOLD
                        if should_save:
                            img_name = f"{file_name}_gemini_keyframe_{keyframe_count}_{uuid.uuid4().hex[:8]}.jpg"
                            img_path = self.output_dir / img_name
                            shutil.copy(str(temp_frame_path), str(img_path))
                            frames.append(
                                {
                                    "path": str(img_path),
                                    "timestamp": timestamp_seconds,
                                    "timestamp_label": self._format_timestamp(timestamp_seconds),
                                }
                            )
                            last_phash = current_phash
                            keyframe_count += 1

                        try:
                            temp_frame_path.unlink()
                        except Exception:
                            pass

                    frame_count += 1
                    if keyframe_count >= MAX_KEYFRAMES:
                        break
            finally:
                await loop.run_in_executor(executor, cap.release)

        return {"frames": frames}

    async def _build_gemini_frame_summaries(self, frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for frame in frames:
            analysis = await self.gemini_service.analyze_image(
                frame["path"],
                prompt=(
                    "请分析这个教学视频关键帧，提取画面中的知识点、实验过程或适合放入课件的视觉要素。"
                    "以 JSON 返回，字段包含 summary、knowledge_points、style_cues、searchable_text。"
                ),
            )
            results.append(
                {
                    "timestamp": frame["timestamp"],
                    "timestamp_label": frame["timestamp_label"],
                    "description": analysis.get("summary") or analysis.get("searchable_text") or "",
                    "knowledge_points": analysis.get("knowledge_points") or [],
                    "style_cues": analysis.get("style_cues") or [],
                }
            )
        return results

    async def _extract_frames_with_vision(self, file_path: Path, file_name: str, task_temp_dir: Path) -> dict[str, Any]:
        chunks: list[ParsedChunk] = []
        images: list[str] = []
        loop = asyncio.get_event_loop()
        last_phash: Optional[imagehash.ImageHash] = None

        with ThreadPoolExecutor() as executor:
            cap = await loop.run_in_executor(executor, cv2.VideoCapture, str(file_path))
            if not cap.isOpened():
                logger.error("无法打开视频: %s", file_path)
                return {"chunks": chunks, "images": images}

            try:
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps <= 0:
                    fps = 1
                frame_interval = max(int(fps * self.interval_seconds), 1)
                frame_count = 0
                keyframe_count = 0

                while True:
                    ret, frame = await loop.run_in_executor(executor, cap.read)
                    if not ret:
                        break

                    if frame_count % frame_interval == 0:
                        timestamp_seconds = frame_count / fps
                        timestamp_str = self._format_timestamp(timestamp_seconds)
                        temp_frame_path = task_temp_dir / f"frame_{frame_count}.jpg"
                        cv2.imwrite(str(temp_frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

                        current_phash = await loop.run_in_executor(
                            executor,
                            imagehash.phash,
                            Image.open(str(temp_frame_path)),
                        )
                        should_save = last_phash is None or (current_phash - last_phash) > PHASH_THRESHOLD
                        if should_save:
                            img_name = f"{file_name}_keyframe_{keyframe_count}_{uuid.uuid4().hex[:8]}.jpg"
                            img_path = self.output_dir / img_name
                            shutil.copy(str(temp_frame_path), str(img_path))
                            images.append(str(img_path))

                            if self.vision_service:
                                try:
                                    description = await self.vision_service.describe_video_frame(
                                        image_path=str(img_path),
                                        timestamp=timestamp_seconds,
                                    )
                                except Exception as exc:
                                    logger.warning("Legacy frame vision failed: %s", exc)
                                    description = f"[视频关键帧 at {timestamp_str}] (视觉理解失败)"
                            else:
                                description = self._generate_frame_description(
                                    frame.shape[1],
                                    frame.shape[0],
                                    timestamp_str,
                                )

                            chunks.append(
                                ParsedChunk(
                                    content=f"[视频关键帧 at {timestamp_str}]\n{description}",
                                    metadata={
                                        "source": file_name,
                                        "timestamp": timestamp_seconds,
                                        "type": "visual",
                                        "has_image": True,
                                        "frame_number": keyframe_count,
                                    },
                                )
                            )
                            last_phash = current_phash
                            keyframe_count += 1

                        try:
                            temp_frame_path.unlink()
                        except Exception:
                            pass

                    frame_count += 1
                    if keyframe_count >= MAX_KEYFRAMES:
                        break
            finally:
                await loop.run_in_executor(executor, cap.release)

        return {"chunks": chunks, "images": images}

    async def _extract_and_transcribe_audio(
        self,
        file_path: Path,
        file_name: str,
        task_temp_dir: Path,
    ) -> list[ParsedChunk]:
        if not self.api_key or not self.asr_service:
            logger.warning("未配置 DASHSCOPE_API_KEY，跳过音频转录")
            return []

        temp_audio_path: Optional[Path] = None
        try:
            temp_audio_path = await self._extract_audio(file_path, task_temp_dir)
            if temp_audio_path is None or not temp_audio_path.exists():
                logger.warning("音频提取失败或视频无音轨")
                return []
            return await self._transcribe_audio(temp_audio_path, file_name)
        finally:
            if temp_audio_path and temp_audio_path.exists():
                try:
                    temp_audio_path.unlink()
                except Exception:
                    pass

    async def _extract_audio(self, video_path: Path, task_temp_dir: Path) -> Optional[Path]:
        audio_path = task_temp_dir / f"audio_{uuid.uuid4().hex}.mp3"
        try:
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(
                stream,
                str(audio_path),
                acodec="libmp3lame",
                ar=ASR_SAMPLE_RATE,
                ac=1,
                bitrate="128k",
            )
            ffmpeg.run(stream, overwrite_output=True, quiet=True, capture_stdout=True, capture_stderr=True)
            if audio_path.exists() and audio_path.stat().st_size > 0:
                return audio_path
        except ffmpeg.Error as exc:
            logger.warning("ffmpeg audio extraction failed: %s", exc.stderr.decode() if exc.stderr else str(exc))
        except Exception as exc:
            logger.warning("Audio extraction failed: %s", exc)
        return None

    async def _transcribe_audio(self, audio_path: Path, source_filename: str) -> list[ParsedChunk]:
        if not self.asr_service:
            return []

        chunks: list[ParsedChunk] = []
        try:
            result = await self.asr_service.recognize(
                audio_path=str(audio_path),
                language="zh",
                enable_itn=True,
                enable_timestamp=False,
            )
            text = str(result.get("text") or "").strip()
            if text:
                chunks.append(
                    ParsedChunk(
                        content=f"[音频转录] {text}",
                        metadata={
                            "source": source_filename,
                            "type": "audio",
                            "start_time": 0.0,
                            "end_time": self._get_audio_duration(audio_path),
                        },
                    )
                )
        except Exception as exc:
            logger.error("Audio transcription failed: %s", exc)
        return chunks

    def _get_audio_duration(self, audio_path: Path) -> float:
        try:
            probe = ffmpeg.probe(str(audio_path))
            return float(probe.get("format", {}).get("duration") or 0.0)
        except Exception:
            return 0.0

    def _merge_multimodal_chunks(
        self,
        visual_chunks: list[ParsedChunk],
        audio_chunks: list[ParsedChunk],
    ) -> list[ParsedChunk]:
        if not visual_chunks and not audio_chunks:
            return []
        if not visual_chunks:
            return audio_chunks
        if not audio_chunks:
            return visual_chunks

        time_blocks: dict[int, dict[str, Any]] = {}
        for chunk in visual_chunks:
            ts = float(chunk.metadata.get("timestamp") or 0.0)
            block_idx = int(ts // TIME_BLOCK_SECONDS)
            time_blocks.setdefault(block_idx, {"visual": [], "audio": None})
            time_blocks[block_idx]["visual"].append(chunk)

        for chunk in audio_chunks:
            start_ts = float(chunk.metadata.get("start_time") or 0.0)
            end_ts = float(chunk.metadata.get("end_time") or start_ts)
            for block_idx in range(int(start_ts // TIME_BLOCK_SECONDS), int(end_ts // TIME_BLOCK_SECONDS) + 1):
                time_blocks.setdefault(block_idx, {"visual": [], "audio": None})
                if time_blocks[block_idx]["audio"] is None:
                    time_blocks[block_idx]["audio"] = chunk

        merged: list[ParsedChunk] = []
        for block_idx in sorted(time_blocks.keys()):
            block = time_blocks[block_idx]
            visual_in_block = block["visual"]
            audio_in_block = block["audio"]
            block_start = block_idx * TIME_BLOCK_SECONDS
            block_end = (block_idx + 1) * TIME_BLOCK_SECONDS
            block_label = f"{self._format_timestamp(block_start)}-{self._format_timestamp(block_end)}"

            content_parts: list[str] = []
            metadata: dict[str, Any] = {
                "source": visual_chunks[0].metadata.get("source", "unknown"),
                "type": "multimodal",
                "time_block": block_label,
                "block_start": block_start,
                "block_end": block_end,
                "has_visual": bool(visual_in_block),
                "has_audio": audio_in_block is not None,
                "frame_count": len(visual_in_block),
            }

            if visual_in_block:
                visual_text = "\n\n".join(f"【看到】{chunk.content}" for chunk in visual_in_block)
                content_parts.append(visual_text)
                metadata["timestamp"] = visual_in_block[0].metadata.get("timestamp")
                metadata["frame_number"] = visual_in_block[0].metadata.get("frame_number")

            if audio_in_block:
                audio_text = str(audio_in_block.content or "").replace("[音频转录]", "【听到】")
                content_parts.append(audio_text)
                metadata["audio_start_time"] = audio_in_block.metadata.get("start_time")
                metadata["audio_end_time"] = audio_in_block.metadata.get("end_time")

            if content_parts:
                merged.append(
                    ParsedChunk(
                        content=f"[时间块 {block_label}]\n\n" + "\n\n".join(content_parts),
                        metadata=metadata,
                    )
                )
        return merged

    def _format_timestamp(self, seconds: float) -> str:
        return str(timedelta(seconds=int(seconds)))

    def _generate_frame_description(self, width: int, height: int, timestamp: str) -> str:
        aspect_ratio = width / height if height > 0 else 1
        if aspect_ratio > 1.7:
            ratio_desc = "wide"
        elif aspect_ratio < 0.8:
            ratio_desc = "tall"
        else:
            ratio_desc = "standard"
        return f"Video frame at {timestamp}, resolution {width}x{height}, {ratio_desc} aspect ratio"

    async def _cleanup_temp_files(self, task_temp_dir: Path):
        try:
            if task_temp_dir.exists():
                shutil.rmtree(task_temp_dir)
        except Exception as exc:
            logger.warning("Failed to cleanup temp files: %s", exc)
