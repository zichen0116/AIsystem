import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

os.environ["DEBUG"] = "false"

if "langgraph.graph.message" not in sys.modules:
    langgraph_module = types.ModuleType("langgraph")
    graph_module = types.ModuleType("langgraph.graph")
    message_module = types.ModuleType("langgraph.graph.message")
    message_module.add_messages = lambda messages, new_messages: messages + new_messages
    graph_module.message = message_module
    langgraph_module.graph = graph_module
    sys.modules["langgraph"] = langgraph_module
    sys.modules["langgraph.graph"] = graph_module
    sys.modules["langgraph.graph.message"] = message_module

from app.api.ppt import download_result


class _FakeQueryResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class PptDownloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_download_result_falls_back_to_stored_file_url_when_refresh_fails(self):
        ppt_result = types.SimpleNamespace(
            id=9,
            docmee_ppt_id="ppt-9",
            file_url="https://stored.example.com/demo.pptx",
        )
        db = types.SimpleNamespace(
            execute=AsyncMock(return_value=_FakeQueryResult(ppt_result)),
            flush=AsyncMock(),
        )
        user = types.SimpleNamespace(id=2)

        with patch(
            "app.api.ppt.docmee_client.download_pptx",
            AsyncMock(side_effect=RuntimeError("refresh failed")),
        ) as mocked_download:
            result = await download_result(9, user=user, db=db)

        self.assertEqual(result, {"file_url": "https://stored.example.com/demo.pptx"})
        mocked_download.assert_awaited_once_with("ppt-9", refresh=True)
        db.flush.assert_not_awaited()

    async def test_download_result_updates_file_url_when_refresh_succeeds(self):
        ppt_result = types.SimpleNamespace(
            id=9,
            docmee_ppt_id="ppt-9",
            file_url="https://old.example.com/demo.pptx",
        )
        db = types.SimpleNamespace(
            execute=AsyncMock(return_value=_FakeQueryResult(ppt_result)),
            flush=AsyncMock(),
        )
        user = types.SimpleNamespace(id=2)

        with patch(
            "app.api.ppt.docmee_client.download_pptx",
            AsyncMock(return_value="https://new.example.com/demo.pptx"),
        ) as mocked_download:
            result = await download_result(9, user=user, db=db)

        self.assertEqual(result, {"file_url": "https://new.example.com/demo.pptx"})
        self.assertEqual(ppt_result.file_url, "https://new.example.com/demo.pptx")
        mocked_download.assert_awaited_once_with("ppt-9", refresh=True)
        db.flush.assert_awaited_once()

    async def test_download_result_raises_502_when_no_refresh_or_stored_url_is_available(self):
        ppt_result = types.SimpleNamespace(
            id=9,
            docmee_ppt_id="ppt-9",
            file_url=None,
        )
        db = types.SimpleNamespace(
            execute=AsyncMock(return_value=_FakeQueryResult(ppt_result)),
            flush=AsyncMock(),
        )
        user = types.SimpleNamespace(id=2)

        with patch(
            "app.api.ppt.docmee_client.download_pptx",
            AsyncMock(side_effect=RuntimeError("refresh failed")),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await download_result(9, user=user, db=db)

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("获取下载地址失败", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
