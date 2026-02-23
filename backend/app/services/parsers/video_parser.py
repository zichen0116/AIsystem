"""
视频解析器
使用 OpenCV 抽取关键帧，ffmpeg 提取音频，qwen3-asr-flash 语音转文字
配合 qwen-vl-plus 视觉理解模型分析关键帧内容
"""
import cv2
import os
import uuid
import logging
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Any, Optional, Tuple
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor

import ffmpeg
import imagehash
from PIL import Image

from app.services.parsers.base import BaseParser, ParsedChunk, ParseResult
from app.services.ai.asr_service import QwenASRService, get_asr_service
from app.services.ai.vision_service import VisionService, get_vision_service

logger = logging.getLogger(__name__)

# 阿里云 ASR 采样率要求
ASR_SAMPLE_RATE = 16000

# 感知哈希差异阈值（大于此值认为是不同画面）
PHASH_THRESHOLD = 5

# 视频解析配置
MAX_KEYFRAMES = 15  # 单个视频最多关键帧数
TIME_BLOCK_SECONDS = 20  # 时间窗口大小（秒）


class VideoParser(BaseParser):
    """
    视频解析器

    核心功能：
    1. 使用 OpenCV 读取视频，抽取关键帧（基于感知哈希去重）
    2. 使用 ffmpeg-python 提取音频
    3. 使用阿里云百炼 qwen3-asr-flash 转录音频
    4. 使用 qwen-vl-plus 视觉模型分析关键帧内容
    """

    def __init__(
        self,
        output_dir: str = "media/extracted",
        interval_seconds: int = 2,
        api_key: Optional[str] = None
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.interval_seconds = interval_seconds
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")

        # 初始化 ASR 服务
        if self.api_key:
            self.asr_service = QwenASRService(api_key=self.api_key)
            self.vision_service = VisionService(api_key=self.api_key)
        else:
            self.asr_service = None
            self.vision_service = None

        # 临时文件目录
        self.temp_dir = Path("media/temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    @property
    def supported_extensions(self) -> list[str]:
        return [".mp4", ".avi", ".mov", ".mkv", ".flv"]

    async def parse(self, file_path: Path) -> ParseResult:
        """
        解析视频文件

        Args:
            file_path: 视频文件路径

        Returns:
            ParseResult: 包含文本块列表和图片路径列表
        """
        chunks: list[ParsedChunk] = []
        images: list[str] = []

        file_name = file_path.name

        # 创建临时目录用于本次解析
        task_temp_dir = self.temp_dir / f"video_{uuid.uuid4().hex}"
        task_temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # ============================================
            # 第一部分：视觉帧提取 + 视觉理解
            # ============================================
            try:
                frames_result = await self._extract_frames_with_vision(
                    file_path, file_name, task_temp_dir
                )
                chunks.extend(frames_result["chunks"])
                images.extend(frames_result["images"])
            except Exception as e:
                logger.error(f"视觉帧提取失败: {e}")

            # ============================================
            # 第二部分：音频转录
            # ============================================
            audio_chunks: list[ParsedChunk] = []

            try:
                audio_chunks = await self._extract_and_transcribe_audio(
                    file_path, file_name, task_temp_dir
                )
            except Exception as e:
                # 音频处理失败不影响视频帧解析
                logger.warning(f"音频转录失败，继续使用视觉解析结果: {e}")

            # ============================================
            # 第三部分：多模态融合
            # ============================================
            # 按时间戳合并视觉和听觉内容
            all_chunks = self._merge_multimodal_chunks(chunks, audio_chunks)

            logger.info(
                f"视频解析完成: {file_name}, "
                f"共 {len(all_chunks)} 个文本块, {len(images)} 张关键帧"
            )

            return ParseResult(chunks=all_chunks, images=images)

        finally:
            # ============================================
            # 第四部分：资源清理
            # ============================================
            # 清理本次解析的临时目录
            await self._cleanup_temp_files(task_temp_dir)

    async def _extract_frames_with_vision(
        self,
        file_path: Path,
        file_name: str,
        task_temp_dir: Path
    ) -> dict:
        """
        提取视频关键帧并进行视觉理解

        策略：
        1. 每 2 秒读取一帧
        2. 使用感知哈希(pHash)去重
        3. 只有画面变化明显(hash_diff > 5)时才保存为关键帧
        4. 对关键帧调用视觉模型进行内容分析
        """
        chunks: list[ParsedChunk] = []
        images: list[str] = []

        # 用于存储上一张关键帧的 pHash
        last_phash: Optional[imagehash.ImageHash] = None
        last_frame_path: Optional[str] = None

        # 使用线程池执行同步的 OpenCV 操作
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            cap = await loop.run_in_executor(
                executor,
                cv2.VideoCapture,
                str(file_path)
            )

            if not cap.isOpened():
                logger.error(f"无法打开视频: {file_path}")
                return {"chunks": chunks, "images": images}

            try:
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = total_frames / fps if fps > 0 else 0

                logger.info(f"视频信息: {file_name}, FPS: {fps}, 时长: {duration:.2f}秒")

                # 每 2 秒一帧
                frame_interval = int(fps * self.interval_seconds)
                frame_count = 0
                keyframe_count = 0

                while True:
                    ret, frame = await loop.run_in_executor(
                        executor,
                        cap.read
                    )

                    if not ret:
                        break

                    if frame_count % frame_interval == 0:
                        timestamp_seconds = frame_count / fps
                        timestamp_str = self._format_timestamp(timestamp_seconds)

                        # 保存临时帧用于计算哈希
                        temp_frame_path = task_temp_dir / f"frame_{frame_count}.jpg"
                        cv2.imwrite(str(temp_frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

                        try:
                            # 计算感知哈希
                            current_phash = await loop.run_in_executor(
                                executor,
                                imagehash.phash,
                                Image.open(str(temp_frame_path))
                            )

                            # 判断是否需要保存为关键帧
                            should_save = False
                            if last_phash is None:
                                # 第一帧直接保存
                                should_save = True
                            else:
                                # 计算哈希差异
                                hash_diff = current_phash - last_phash
                                if hash_diff > PHASH_THRESHOLD:
                                    should_save = True
                                    logger.debug(f"帧 {timestamp_str}: hash_diff={hash_diff}, 保存为关键帧")

                            if should_save:
                                # 生成关键帧文件名
                                img_name = f"{file_name}_keyframe_{keyframe_count}_{uuid.uuid4().hex[:8]}.jpg"
                                img_path = self.output_dir / img_name

                                # 复制文件
                                shutil.copy(str(temp_frame_path), str(img_path))
                                images.append(str(img_path))

                                # 视觉理解（异步）
                                if self.vision_service:
                                    try:
                                        description = await self.vision_service.describe_video_frame(
                                            image_path=str(img_path),
                                            timestamp=timestamp_seconds
                                        )

                                        chunk = ParsedChunk(
                                            content=f"[视频关键帧 at {timestamp_str}]\n{description}",
                                            metadata={
                                                "source": file_name,
                                                "timestamp": timestamp_seconds,
                                                "type": "visual",
                                                "has_image": True,
                                                "frame_number": keyframe_count
                                            }
                                        )
                                    except Exception as e:
                                        logger.warning(f"视觉理解失败: {e}")
                                        chunk = ParsedChunk(
                                            content=f"[视频关键帧 at {timestamp_str}] (视觉理解失败)",
                                            metadata={
                                                "source": file_name,
                                                "timestamp": timestamp_seconds,
                                                "type": "visual",
                                                "has_image": True,
                                                "frame_number": keyframe_count,
                                                "vision_error": str(e)
                                            }
                                        )
                                else:
                                    # 没有配置视觉服务时使用基础描述
                                    description = self._generate_frame_description(
                                        frame.shape[1], frame.shape[0], timestamp_str
                                    )
                                    chunk = ParsedChunk(
                                        content=f"[视频关键帧 at {timestamp_str}]\n{description}",
                                        metadata={
                                            "source": file_name,
                                            "timestamp": timestamp_seconds,
                                            "type": "visual",
                                            "has_image": True,
                                            "frame_number": keyframe_count
                                        }
                                    )

                                chunks.append(chunk)
                                keyframe_count += 1

                                # 更新上一帧哈希
                                last_phash = current_phash
                                last_frame_path = str(img_path)

                                logger.info(f"关键帧: {timestamp_str} -> {img_name}")

                        except Exception as e:
                            logger.warning(f"帧处理失败: {e}")

                        # 清理临时帧
                        try:
                            temp_frame_path.unlink()
                        except:
                            pass

                    frame_count += 1

                    # 限制最大关键帧数（防止费用爆炸）
                    if keyframe_count >= MAX_KEYFRAMES:
                        logger.info(f"达到最大关键帧数限制 ({MAX_KEYFRAMES})")
                        break

            finally:
                await loop.run_in_executor(executor, cap.release)

        return {"chunks": chunks, "images": images}

    async def _extract_and_transcribe_audio(
        self,
        file_path: Path,
        file_name: str,
        task_temp_dir: Path
    ) -> list[ParsedChunk]:
        """
        提取音频并转录

        Args:
            file_path: 视频文件路径
            file_name: 视频文件名
            task_temp_dir: 任务临时目录

        Returns:
            list[ParsedChunk]: 音频转录文本块列表
        """
        if not self.api_key:
            logger.warning("未配置 DASHSCOPE_API_KEY，跳过音频转录")
            return []

        if not self.asr_service:
            logger.warning("ASR 服务未初始化，跳过音频转录")
            return []

        # 创建临时音频文件
        temp_audio_path: Optional[Path] = None

        try:
            # 提取音频
            temp_audio_path = await self._extract_audio(file_path, task_temp_dir)

            if temp_audio_path is None or not temp_audio_path.exists():
                logger.warning("音频提取失败或视频无音轨")
                return []

            # 转录音频
            transcription_chunks = await self._transcribe_audio(temp_audio_path, file_name)

            logger.info(f"音频转录完成，共 {len(transcription_chunks)} 段")
            return transcription_chunks

        finally:
            # 清理临时音频文件
            if temp_audio_path and temp_audio_path.exists():
                try:
                    temp_audio_path.unlink()
                    logger.debug(f"已删除临时音频文件: {temp_audio_path}")
                except Exception as e:
                    logger.warning(f"删除临时音频文件失败: {e}")

    async def _extract_audio(self, video_path: Path, task_temp_dir: Path) -> Optional[Path]:
        """
        使用 ffmpeg-python 提取音频

        Args:
            video_path: 视频文件路径
            task_temp_dir: 任务临时目录

        Returns:
            Optional[Path]: 临时音频文件路径，失败返回 None
        """
        audio_path = task_temp_dir / f"audio_{uuid.uuid4().hex}.mp3"

        try:
            # 使用 ffmpeg-python 提取音频并转码为 MP3
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(
                stream,
                str(audio_path),
                acodec='libmp3lame',           # MP3 编码器
                ar=ASR_SAMPLE_RATE,            # 16kHz 采样率
                ac=1,                          # 单声道
                bitrate='128k'                 # 比特率
            )
            ffmpeg.run(stream, overwrite_output=True, quiet=True, capture_stdout=True, capture_stderr=True)

            if audio_path.exists() and audio_path.stat().st_size > 0:
                logger.debug(f"音频提取成功: {audio_path}")
                return audio_path
            else:
                logger.warning("音频文件为空，可能视频无音轨")
                return None

        except ffmpeg.Error as e:
            logger.warning(f"ffmpeg 音频提取失败: {e.stderr.decode() if e.stderr else str(e)}")
            return None
        except Exception as e:
            logger.warning(f"音频提取异常: {e}")
            return None

    async def _transcribe_audio(
        self, audio_path: Path, source_filename: str
    ) -> list[ParsedChunk]:
        """
        使用阿里云百炼 qwen3-asr-flash 转录音频

        Args:
            audio_path: 音频文件路径
            source_filename: 源视频文件名

        Returns:
            list[ParsedChunk]: 转录结果列表
        """
        if not self.asr_service:
            logger.warning("ASR 服务未初始化，跳过音频转录")
            return []

        chunks: list[ParsedChunk] = []

        try:
            # 调用 qwen3-asr-flash 进行语音识别
            logger.info(f"开始 ASR 转录: {audio_path}")

            # 识别音频
            result = await self.asr_service.recognize(
                audio_path=str(audio_path),
                language="zh",  # 默认中文
                enable_itn=True,  # 启用逆文本规范化
                enable_timestamp=False  # 简化处理，暂不解析时间戳
            )

            text = result.get("text", "").strip()

            if text:
                # 获取音频时长
                duration = self._get_audio_duration(audio_path)

                chunk = ParsedChunk(
                    content=f"[音频转录] {text}",
                    metadata={
                        "source": source_filename,
                        "type": "audio",
                        "start_time": 0.0,
                        "end_time": duration
                    }
                )
                chunks.append(chunk)
                logger.info(f"ASR 转录成功，文本长度: {len(text)}")
            else:
                logger.warning("ASR 转录结果为空")

        except Exception as e:
            logger.error(f"音频转录异常: {e}")
            # 不抛出异常，让解析继续

        return chunks

    def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频文件时长"""
        try:
            cap = cv2.VideoCapture(str(audio_path))
            if cap.isOpened():
                duration = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                cap.release()
                return duration
        except:
            pass
        return 0.0

    def _merge_multimodal_chunks(
        self,
        visual_chunks: list[ParsedChunk],
        audio_chunks: list[ParsedChunk]
    ) -> list[ParsedChunk]:
        """
        合并视觉帧和音频转录结果 - 时空对齐

        策略：
        1. 将视频按 TIME_BLOCK_SECONDS(20秒) 划分为时间块
        2. 同一时间块内的视觉描述和语音转录进行拼接合并
        3. 合并后的内容包含 "看到的内容" + "听到的内容"

        Args:
            visual_chunks: 视觉帧解析结果
            audio_chunks: 音频转录结果

        Returns:
            list[ParsedChunk]: 时空对齐合并后的结果
        """
        merged: list[ParsedChunk] = []

        if not visual_chunks and not audio_chunks:
            return merged

        # 如果没有视觉或音频，直接返回现有的
        if not visual_chunks:
            return audio_chunks
        if not audio_chunks:
            return visual_chunks

        # 构建时间块字典
        # key: 时间块索引 (0, 1, 2...)
        # value: {"visual": [...], "audio": ...}
        time_blocks: dict[int, dict] = {}

        # 将视觉帧分配到时间块
        for chunk in visual_chunks:
            ts = chunk.metadata.get("timestamp", 0.0)
            block_idx = int(ts // TIME_BLOCK_SECONDS)
            if block_idx not in time_blocks:
                time_blocks[block_idx] = {"visual": [], "audio": None}
            time_blocks[block_idx]["visual"].append(chunk)

        # 将音频转录分配到时间块（音频是整段的，根据起始时间分配）
        for chunk in audio_chunks:
            start_ts = chunk.metadata.get("start_time", 0.0)
            end_ts = chunk.metadata.get("end_time", start_ts)

            # 音频可能跨越多个时间块
            start_block = int(start_ts // TIME_BLOCK_SECONDS)
            end_block = int(end_ts // TIME_BLOCK_SECONDS)

            for block_idx in range(start_block, end_block + 1):
                if block_idx not in time_blocks:
                    time_blocks[block_idx] = {"visual": [], "audio": None}
                # 保留音频原始块（不拆分，保持完整性）
                if time_blocks[block_idx]["audio"] is None:
                    time_blocks[block_idx]["audio"] = chunk

        # 按时间块顺序合并
        for block_idx in sorted(time_blocks.keys()):
            block = time_blocks[block_idx]
            visual_chunks_in_block = block.get("visual", [])
            audio_chunk_in_block = block.get("audio")

            # 计算该时间块的起始时间
            block_start_time = block_idx * TIME_BLOCK_SECONDS
            block_end_time = (block_idx + 1) * TIME_BLOCK_SECONDS
            block_time_str = f"{self._format_timestamp(block_start_time)}-{self._format_timestamp(block_end_time)}"

            # 合并内容
            content_parts = []
            merged_metadata = {
                "source": visual_chunks[0].metadata.get("source", "unknown") if visual_chunks else "unknown",
                "type": "multimodal",
                "time_block": block_time_str,
                "block_start": block_start_time,
                "block_end": block_end_time,
                "has_visual": len(visual_chunks_in_block) > 0,
                "has_audio": audio_chunk_in_block is not None,
                "frame_count": len(visual_chunks_in_block),
            }

            # 添加视觉描述
            if visual_chunks_in_block:
                visual_content = "\n\n".join([
                    f"【看到】{chunk.content}"
                    for chunk in visual_chunks_in_block
                ])
                content_parts.append(visual_content)
                # 继承第一个视觉块的元数据
                merged_metadata.update({
                    "timestamp": visual_chunks_in_block[0].metadata.get("timestamp"),
                    "frame_number": visual_chunks_in_block[0].metadata.get("frame_number"),
                })

            # 添加音频转录
            if audio_chunk_in_block:
                audio_text = audio_chunk_in_block.content.replace("[音频转录]", "【听到】")
                content_parts.append(audio_text)
                # 合并音频时间信息
                merged_metadata.update({
                    "audio_start_time": audio_chunk_in_block.metadata.get("start_time"),
                    "audio_end_time": audio_chunk_in_block.metadata.get("end_time"),
                })

            # 创建合并后的 chunk
            if content_parts:
                merged_content = f"[时间块 {block_time_str}]\n\n" + "\n\n".join(content_parts)

                merged_chunk = ParsedChunk(
                    content=merged_content,
                    metadata=merged_metadata
                )
                merged.append(merged_chunk)

        logger.info(f"时空对齐完成: {len(merged)} 个时间块")
        return merged

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳"""
        td = timedelta(seconds=int(seconds))
        return str(td)

    def _generate_frame_description(
        self, width: int, height: int, timestamp: str
    ) -> str:
        """
        生成帧描述（无视觉理解时的备用方案）

        Args:
            width: 帧宽度
            height: 帧高度
            timestamp: 时间戳

        Returns:
            str: 帧描述
        """
        aspect_ratio = width / height if height > 0 else 1

        if aspect_ratio > 1.7:
            ratio_desc = "wide (16:9 or similar)"
        elif aspect_ratio < 0.8:
            ratio_desc = "tall (9:16 or similar)"
        else:
            ratio_desc = "standard"

        return f"Video frame at {timestamp}, resolution {width}x{height}, {ratio_desc} aspect ratio"

    async def _cleanup_temp_files(self, task_temp_dir: Path):
        """清理临时文件"""
        try:
            if task_temp_dir.exists():
                shutil.rmtree(task_temp_dir)
                logger.debug(f"已清理临时目录: {task_temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
