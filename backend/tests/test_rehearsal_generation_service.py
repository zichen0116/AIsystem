import unittest

from app.services.rehearsal_generation_service import (
    finalize_actions_for_slide,
    merge_tts_results_into_actions,
    normalize_actions_for_page_position,
)


class RehearsalGenerationServiceTests(unittest.TestCase):
    def test_merge_tts_results_returns_new_nested_actions(self):
        original_actions = [
            {
                "type": "speech",
                "text": "hello",
                "audio_status": "pending",
            },
            {
                "type": "spotlight",
                "elementId": "el_1",
            },
        ]

        merged = merge_tts_results_into_actions(
            original_actions,
            [
                {
                    "temp_audio_url": "https://temp.example/audio.wav",
                    "persistent_audio_url": "https://oss.example/audio.wav",
                    "audio_status": "ready",
                }
            ],
        )

        self.assertIsNot(merged, original_actions)
        self.assertEqual(original_actions[0]["audio_status"], "pending")
        self.assertNotIn("temp_audio_url", original_actions[0])
        self.assertEqual(merged[0]["audio_status"], "ready")
        self.assertEqual(merged[0]["temp_audio_url"], "https://temp.example/audio.wav")
        self.assertEqual(merged[0]["persistent_audio_url"], "https://oss.example/audio.wav")

    def test_normalize_actions_keeps_first_page_greeting(self):
        actions = [{"type": "speech", "text": "同学们好，今天我们来学习分数"}]
        normalized = normalize_actions_for_page_position(actions, scene_order=0, title="分数")
        self.assertEqual(normalized[0]["text"], "同学们好，今天我们来学习分数")

    def test_normalize_actions_strips_non_first_page_greeting(self):
        actions = [{"type": "speech", "text": "同学们好，今天我们来学习分数的加减法"}]
        normalized = normalize_actions_for_page_position(actions, scene_order=1, title="分数")
        self.assertEqual(normalized[0]["text"], "分数的加减法")

    def test_finalize_actions_falls_back_to_valid_focus_element(self):
        slide = {
            "elements": [
                {"id": "title_1", "type": "text", "top": 40, "content": "<p>标题</p>"},
                {"id": "body_1", "type": "text", "top": 160, "content": "<p>重点知识</p>"},
            ]
        }
        actions = [{"type": "spotlight", "elementId": "missing"}]

        finalized = finalize_actions_for_slide(
            actions,
            outline={"title": "测试页", "description": "讲解内容"},
            slide_content=slide,
            scene_order=0,
        )

        self.assertEqual(finalized[0]["type"], "spotlight")
        self.assertEqual(finalized[0]["elementId"], "body_1")
        self.assertEqual(finalized[1]["type"], "speech")

    def test_finalize_actions_injects_visual_action_when_missing(self):
        slide = {
            "elements": [
                {"id": "title_1", "type": "text", "top": 40, "content": "<p>标题</p>"},
                {"id": "body_1", "type": "text", "top": 160, "content": "<p>重点知识</p>"},
            ]
        }
        actions = [{"type": "speech", "text": "先讲正文"}]

        finalized = finalize_actions_for_slide(
            actions,
            outline={"title": "测试页", "description": "讲解内容"},
            slide_content=slide,
            scene_order=0,
        )

        self.assertEqual(finalized[0]["type"], "spotlight")
        self.assertEqual(finalized[0]["elementId"], "body_1")
        self.assertEqual(finalized[1]["type"], "speech")

    def test_finalize_actions_supports_highlight(self):
        slide = {
            "elements": [
                {"id": "body_1", "type": "text", "top": 160, "content": "<p>重点知识</p>"},
                {"id": "body_2", "type": "text", "top": 230, "content": "<p>补充知识</p>"},
            ]
        }
        actions = [{"type": "highlight", "elementIds": ["body_1", "body_2"]}]

        finalized = finalize_actions_for_slide(
            actions,
            outline={"title": "测试页", "description": "讲解内容"},
            slide_content=slide,
            scene_order=0,
        )

        self.assertEqual(finalized[0]["type"], "highlight")
        self.assertEqual(finalized[0]["elementIds"], ["body_1", "body_2"])
        self.assertEqual(finalized[1]["type"], "speech")


if __name__ == "__main__":
    unittest.main()
