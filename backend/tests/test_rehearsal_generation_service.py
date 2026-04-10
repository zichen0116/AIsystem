import unittest

from app.services.rehearsal_generation_service import merge_tts_results_into_actions


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


if __name__ == "__main__":
    unittest.main()
