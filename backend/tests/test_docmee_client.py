import os
import unittest
from unittest.mock import AsyncMock

import httpx

os.environ["DEBUG"] = "false"

from app.services.ppt.docmee_client import (
    DocmeeClient,
    build_docmee_client_kwargs,
    describe_exception,
)


class DocmeeClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_pptx_uses_extended_timeout(self):
        client = DocmeeClient()
        client._request = AsyncMock(return_value={"data": {"pptInfo": {"id": "ppt-1"}}})

        result = await client.generate_pptx("task-1", "tpl-1", "# demo")

        self.assertEqual(result["id"], "ppt-1")
        client._request.assert_awaited_once_with(
            "POST",
            "/api/ppt/v2/generatePptx",
            json={"id": "task-1", "templateId": "tpl-1", "markdown": "# demo"},
            timeout_s=600,
        )

    async def test_finalize_ppt_info_loads_missing_pptx_property(self):
        client = DocmeeClient()
        client.load_pptx = AsyncMock(return_value={
            "id": "ppt-1",
            "pptxProperty": "encoded-pptx",
            "extInfo": {"uploadStatus": "ready"},
        })

        result = await client.finalize_ppt_info(
            {
                "id": "ppt-1",
                "fileUrl": "https://example.com/demo.pptx",
                "pptxProperty": None,
                "extInfo": {"uploadStatus": "processing"},
            },
            poll_attempts=1,
            poll_delay=0,
        )

        self.assertEqual(result["pptxProperty"], "encoded-pptx")
        self.assertEqual(result["fileUrl"], "https://example.com/demo.pptx")
        client.load_pptx.assert_awaited_once_with("ppt-1")

    async def test_finalize_ppt_info_retries_until_property_ready(self):
        client = DocmeeClient()
        client.load_pptx = AsyncMock(side_effect=[
            {"id": "ppt-1", "extInfo": {"uploadStatus": "processing"}},
            {"id": "ppt-1", "pptxProperty": "encoded-pptx", "extInfo": {"uploadStatus": "ready"}},
        ])

        result = await client.finalize_ppt_info(
            {"id": "ppt-1", "extInfo": {"uploadStatus": "processing"}},
            poll_attempts=2,
            poll_delay=0,
        )

        self.assertEqual(result["pptxProperty"], "encoded-pptx")
        self.assertEqual(client.load_pptx.await_count, 2)

    def test_get_page_count_supports_pages_key(self):
        encoded = DocmeeClient.compress_pptx_property({
            "pages": [{}, {}, {}],
            "width": 960,
            "height": 540,
        })

        self.assertEqual(DocmeeClient.get_page_count(encoded), 3)

    def test_describe_exception_uses_class_name_when_message_is_empty(self):
        exc = httpx.ReadTimeout("")
        self.assertEqual(describe_exception(exc), "ReadTimeout")

    def test_build_docmee_client_kwargs_disables_proxy_by_default(self):
        kwargs = build_docmee_client_kwargs(timeout_s=600)

        self.assertEqual(kwargs["timeout"].read, 600)
        self.assertFalse(kwargs["trust_env"])


if __name__ == "__main__":
    unittest.main()
