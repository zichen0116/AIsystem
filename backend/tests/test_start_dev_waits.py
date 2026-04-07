import unittest
from unittest.mock import Mock, patch

from backend import start_dev


class DummyProcess:
    def __init__(self, poll_result=None):
        self._poll_result = poll_result

    def poll(self):
        return self._poll_result


class StartDevWaitTests(unittest.TestCase):
    @patch("backend.start_dev.time.sleep", return_value=None)
    def test_wait_for_condition_retries_until_success(self, _sleep):
        checker = Mock(side_effect=[False, False, True])

        result = start_dev.wait_for_condition(
            "FastAPI",
            checker,
            retries=3,
            interval=0,
        )

        self.assertTrue(result)
        self.assertEqual(checker.call_count, 3)

    @patch("backend.start_dev.time.sleep", return_value=None)
    def test_wait_for_condition_raises_timeout_after_retries(self, _sleep):
        checker = Mock(return_value=False)

        with self.assertRaises(TimeoutError):
            start_dev.wait_for_condition(
                "PostgreSQL",
                checker,
                retries=2,
                interval=0,
            )

        self.assertEqual(checker.call_count, 2)

    @patch("backend.start_dev.time.sleep", return_value=None)
    def test_wait_for_condition_fails_fast_when_process_exits(self, _sleep):
        checker = Mock(return_value=False)
        process = DummyProcess(poll_result=1)

        with self.assertRaises(RuntimeError):
            start_dev.wait_for_condition(
                "FastAPI",
                checker,
                retries=3,
                interval=0,
                process=process,
            )

        self.assertEqual(checker.call_count, 0)


if __name__ == "__main__":
    unittest.main()
