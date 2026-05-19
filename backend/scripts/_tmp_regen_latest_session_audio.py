import asyncio
import json
import traceback
import sys
from pathlib import Path

from sqlalchemy import case, desc, func, select
from sqlalchemy.orm.attributes import flag_modified

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal, engine
from app.models.rehearsal import RehearsalScene, RehearsalSession
from app.services.tts_service import synthesize


async def main() -> None:
    result = {
        "success": False,
        "session_id": None,
        "regeneration_stats": {
            "total_scenes": 0,
            "ready": 0,
            "partial": 0,
            "failed": 0,
        },
        "aggregation": {
            "scene_count": 0,
            "ready_count": 0,
            "partial_count": 0,
            "failed_count": 0,
            "pending_count": 0,
        },
        "errors": [],
    }

    async with AsyncSessionLocal() as db:
        try:
            latest_session = (
                (
                    await db.execute(
                        select(RehearsalSession).order_by(desc(RehearsalSession.id)).limit(1)
                    )
                )
                .scalars()
                .first()
            )

            if latest_session is None:
                result["errors"].append("rehearsal_sessions 中没有数据")
                print(json.dumps(result, ensure_ascii=False))
                return

            session_id = latest_session.id
            result["session_id"] = session_id

            settings = latest_session.settings or {}
            voice = settings.get("voice", "Cherry")
            try:
                speed = float(settings.get("speed", 1.0) or 1.0)
            except Exception:
                speed = 1.0

            scenes = list(
                (
                    await db.execute(
                        select(RehearsalScene)
                        .where(RehearsalScene.session_id == session_id)
                        .order_by(RehearsalScene.scene_order.asc(), RehearsalScene.id.asc())
                    )
                )
                .scalars()
                .all()
            )

            result["regeneration_stats"]["total_scenes"] = len(scenes)

            for scene in scenes:
                actions = list(scene.actions or [])
                total_speech = 0
                success_speech = 0
                scene_errors: list[str] = []

                for action in actions:
                    if not isinstance(action, dict):
                        continue
                    if action.get("type") != "speech" or not action.get("text"):
                        continue

                    total_speech += 1
                    try:
                        tts_result = await synthesize(
                            text=action["text"],
                            voice=voice,
                            speed=speed,
                            user_id=latest_session.user_id,
                        )
                    except Exception as ex:
                        tts_result = {
                            "temp_audio_url": None,
                            "persistent_audio_url": None,
                            "audio_status": "failed",
                        }
                        scene_errors.append(f"speech action TTS异常: {ex}")

                    action["temp_audio_url"] = tts_result.get("temp_audio_url")
                    action["persistent_audio_url"] = tts_result.get("persistent_audio_url")
                    action["audio_status"] = tts_result.get("audio_status", "failed")

                    if action["audio_status"] in ("temp_ready", "ready"):
                        success_speech += 1
                    else:
                        scene_errors.append("speech action TTS失败")

                if total_speech == 0:
                    scene.audio_status = "ready"
                elif success_speech == total_speech:
                    scene.audio_status = "ready"
                elif success_speech > 0:
                    scene.audio_status = "partial"
                else:
                    scene.audio_status = "failed"

                scene.actions = actions
                flag_modified(scene, "actions")
                scene.error_message = "; ".join(scene_errors)[:500] if scene_errors else None

                if scene.audio_status == "ready":
                    result["regeneration_stats"]["ready"] += 1
                elif scene.audio_status == "partial":
                    result["regeneration_stats"]["partial"] += 1
                else:
                    result["regeneration_stats"]["failed"] += 1

            await db.commit()

            aggregate_row = (
                await db.execute(
                    select(
                        func.count(RehearsalScene.id).label("scene_count"),
                        func.sum(
                            case((RehearsalScene.audio_status == "ready", 1), else_=0)
                        ).label("ready_count"),
                        func.sum(
                            case((RehearsalScene.audio_status == "partial", 1), else_=0)
                        ).label("partial_count"),
                        func.sum(
                            case((RehearsalScene.audio_status == "failed", 1), else_=0)
                        ).label("failed_count"),
                        func.sum(
                            case((RehearsalScene.audio_status == "pending", 1), else_=0)
                        ).label("pending_count"),
                    ).where(RehearsalScene.session_id == session_id)
                )
            ).one()

            result["aggregation"] = {
                "scene_count": int(aggregate_row.scene_count or 0),
                "ready_count": int(aggregate_row.ready_count or 0),
                "partial_count": int(aggregate_row.partial_count or 0),
                "failed_count": int(aggregate_row.failed_count or 0),
                "pending_count": int(aggregate_row.pending_count or 0),
            }

            result["success"] = True

        except Exception as ex:
            await db.rollback()
            result["errors"].append(str(ex))
            result["errors"].append(traceback.format_exc())

    await engine.dispose()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
