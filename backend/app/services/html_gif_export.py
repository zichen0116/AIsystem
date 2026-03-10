import os
import re
import shutil
import subprocess
import tempfile
import sys
import asyncio
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import async_playwright


@dataclass
class GifExportResult:
    gif_path: Path
    work_dir: Path


def _sanitize_filename(name: str) -> str:
    name = (name or "").strip() or "demo"
    name = re.sub(r"[^a-zA-Z0-9_\-\.]+", "_", name)
    return name[:80] or "demo"


async def export_html_to_gif(
    *,
    html: str,
    width: int = 960,
    height: int = 540,
    duration_sec: float = 6.0,
    fps: int = 12,
    start_delay_ms: int = 300,
    filename: str = "demo.gif",
) -> GifExportResult:
    """
    Render HTML in headless Chromium, capture frames, encode to GIF via ffmpeg.

    Returns a GifExportResult containing gif_path and work_dir (caller should cleanup work_dir).
    """
    if not html or not html.strip():
        raise ValueError("html 不能为空")
    if width < 200 or width > 1920:
        raise ValueError("width 超出范围（200-1920）")
    if height < 200 or height > 1080:
        raise ValueError("height 超出范围（200-1080）")
    if fps < 1 or fps > 30:
        raise ValueError("fps 超出范围（1-30）")
    if duration_sec <= 0 or duration_sec > 30:
        raise ValueError("duration_sec 超出范围（0-30）")

    # Windows + SelectorEventLoop 时无法创建子进程（Playwright 必需），会抛 NotImplementedError。
    # 为了兼容不同运行环境（如 Anaconda/某些策略），在这种情况下把渲染工作放到独立线程，
    # 在线程内使用 Proactor 事件循环执行。
    if sys.platform.startswith("win"):
        try:
            loop = asyncio.get_running_loop()
            proactor_cls = getattr(asyncio, "ProactorEventLoop", None)
            if (proactor_cls and not isinstance(loop, proactor_cls)) or (
                "Selector" in loop.__class__.__name__
            ):
                return await asyncio.to_thread(
                    _export_html_to_gif_sync,
                    html=html,
                    width=width,
                    height=height,
                    duration_sec=duration_sec,
                    fps=fps,
                    start_delay_ms=start_delay_ms,
                    filename=filename,
                )
        except Exception:
            pass

    return await _export_html_to_gif_impl(
        html=html,
        width=width,
        height=height,
        duration_sec=duration_sec,
        fps=fps,
        start_delay_ms=start_delay_ms,
        filename=filename,
    )


def _export_html_to_gif_sync(
    *,
    html: str,
    width: int,
    height: int,
    duration_sec: float,
    fps: int,
    start_delay_ms: int,
    filename: str,
) -> GifExportResult:
    if sys.platform.startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())  # type: ignore[attr-defined]
        except Exception:
            pass
    return asyncio.run(
        _export_html_to_gif_impl(
            html=html,
            width=width,
            height=height,
            duration_sec=duration_sec,
            fps=fps,
            start_delay_ms=start_delay_ms,
            filename=filename,
        )
    )


async def _export_html_to_gif_impl(
    *,
    html: str,
    width: int,
    height: int,
    duration_sec: float,
    fps: int,
    start_delay_ms: int,
    filename: str,
) -> GifExportResult:
    frames = max(1, int(duration_sec * fps))
    step_ms = int(1000 / fps)

    work_dir = Path(tempfile.mkdtemp(prefix="html_gif_"))
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    gif_name = _sanitize_filename(Path(filename).stem) + ".gif"
    gif_path = work_dir / gif_name

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            try:
                page = await browser.new_page(viewport={"width": int(width), "height": int(height)})

                # set_content will wait for DOMContentLoaded; we add a small delay for scripts/animations to start.
                await page.set_content(html, wait_until="domcontentloaded")
                if start_delay_ms > 0:
                    await page.wait_for_timeout(int(start_delay_ms))

                # If the page exposes a common demo interface, trigger it.
                # (Optional; doesn't fail export if absent)
                try:
                    await page.evaluate(
                        "() => { try { window.__DEMO__?.start?.(); } catch(e) {} }"
                    )
                except Exception:
                    pass

                for i in range(frames):
                    frame_path = frames_dir / f"frame_{i:05d}.png"
                    # full_page=True 确保捕获整页内容（包括需要滚动才能看到的部分）
                    await page.screenshot(path=str(frame_path), type="png", full_page=True)
                    await page.wait_for_timeout(step_ms)
            finally:
                await browser.close()
    except NotImplementedError as e:
        raise RuntimeError(
            "Playwright 启动失败：当前 Windows asyncio 事件循环不支持子进程。"
            "请使用 ProactorEventLoop（或重启后端），或使用 Docker 运行后端。"
        ) from e

    # Encode GIF with palette for better quality.
    palette_path = work_dir / "palette.png"
    input_pattern = str(frames_dir / "frame_%05d.png")

    # 等比缩放：按目标宽度缩放，高度自动（避免裁切），后续再通过 GIF 尺寸控制整体大小
    vf_scale = f"scale={int(width)}:-1:flags=lanczos"
    vf_palette = f"{vf_scale},palettegen=stats_mode=diff"
    vf_use = f"{vf_scale}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5"

    # 1) palettegen
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-framerate",
            str(int(fps)),
            "-i",
            input_pattern,
            "-vf",
            vf_palette,
            str(palette_path),
        ]
    )

    # 2) paletteuse
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-framerate",
            str(int(fps)),
            "-i",
            input_pattern,
            "-i",
            str(palette_path),
            "-lavfi",
            vf_use,
            "-loop",
            "0",
            str(gif_path),
        ]
    )

    return GifExportResult(gif_path=gif_path, work_dir=work_dir)


def _run_ffmpeg(cmd: list[str]) -> None:
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "FFMPEG_FORCE_COLORS": "0"},
        )
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or "").strip()
        raise RuntimeError(f"ffmpeg 执行失败：{detail or 'unknown error'}") from e


def cleanup_export_dir(path: Path) -> None:
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

