import unittest

from app.services.rehearsal_generation_service import (
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


if __name__ == "__main__":
    unittest.main()
