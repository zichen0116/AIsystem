import os
import json
import sys
import types
import unittest
from unittest.mock import patch

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

from app.services.ppt.nodes import modify_slide_json


def _make_text_shape(shape_id: str, placeholder_type: str | None, text: str) -> dict:
    property_payload = {
        "anchor": [0, 0, 100, 20],
    }
    if placeholder_type:
        property_payload["placeholder"] = {"type": placeholder_type}

    return {
        "id": shape_id,
        "pid": "page-1",
        "type": "text",
        "extInfo": {"property": property_payload},
        "children": [
            {
                "id": f"{shape_id}-p-1",
                "pid": shape_id,
                "type": "paragraph",
                "extInfo": {"property": {"lineSpacing": 100}},
                "children": [
                    {
                        "id": f"{shape_id}-r-1",
                        "pid": f"{shape_id}-p-1",
                        "type": "run",
                        "text": text,
                        "extInfo": {"property": {"fontSize": 24}},
                    }
                ],
            }
        ],
    }


def _make_sample_page() -> dict:
    return {
        "id": "page-1",
        "type": "slide",
        "extInfo": {"slideMasterIdx": 0, "background": {"color": "#ffffff"}},
        "children": [
            _make_text_shape("title-shape", "title", "中国文化"),
            _make_text_shape("subtitle-shape", "subTitle", "传统与现代的对话"),
            _make_text_shape("body-shape", "body", "这里还有副标题和正文"),
        ],
    }


def _make_fake_llm_client(page: dict):
    class _FakeCompletions:
        async def create(self, **kwargs):
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message=types.SimpleNamespace(content=json.dumps(page, ensure_ascii=False))
                    )
                ]
            )

    class _FakeChat:
        def __init__(self):
            self.completions = _FakeCompletions()

    return types.SimpleNamespace(chat=_FakeChat())


class PptSlideEditingTests(unittest.IsolatedAsyncioTestCase):
    async def test_modify_slide_json_updates_title_without_rebuilding_page(self):
        page = _make_sample_page()
        pptx_obj = {
            "width": 960,
            "height": 540,
            "pages": [page],
        }

        with patch(
            "app.services.ppt.nodes._get_llm_client",
            side_effect=AssertionError("title-only edits should not call the LLM"),
        ):
            updated_page = await modify_slide_json(
                instruction="把这一页标题改成《走进中国文化》",
                pptx_obj=pptx_obj,
                slide_index=0,
            )

        self.assertEqual(updated_page["id"], "page-1")
        self.assertEqual(len(updated_page["children"]), 3)
        self.assertEqual(
            updated_page["children"][0]["children"][0]["children"][0]["text"],
            "走进中国文化",
        )
        self.assertEqual(
            updated_page["children"][2]["children"][0]["children"][0]["text"],
            "这里还有副标题和正文",
        )

    async def test_modify_slide_json_updates_subtitle_without_rebuilding_page(self):
        page = _make_sample_page()
        pptx_obj = {"width": 960, "height": 540, "pages": [page]}

        with patch(
            "app.services.ppt.nodes._get_llm_client",
            side_effect=AssertionError("subtitle-only edits should not call the LLM"),
        ):
            updated_page = await modify_slide_json(
                instruction="把这一页副标题改成“核心概念与文化气质”",
                pptx_obj=pptx_obj,
                slide_index=0,
            )

        self.assertEqual(
            updated_page["children"][0]["children"][0]["children"][0]["text"],
            "中国文化",
        )
        self.assertEqual(
            updated_page["children"][1]["children"][0]["children"][0]["text"],
            "核心概念与文化气质",
        )
        self.assertEqual(
            updated_page["children"][2]["children"][0]["children"][0]["text"],
            "这里还有副标题和正文",
        )

    async def test_modify_slide_json_updates_body_without_rebuilding_page(self):
        page = _make_sample_page()
        pptx_obj = {"width": 960, "height": 540, "pages": [page]}

        with patch(
            "app.services.ppt.nodes._get_llm_client",
            side_effect=AssertionError("body-only edits should not call the LLM"),
        ):
            updated_page = await modify_slide_json(
                instruction="把这一页正文改成“从礼乐制度、审美观念和日常生活三个角度展开”",
                pptx_obj=pptx_obj,
                slide_index=0,
            )

        self.assertEqual(
            updated_page["children"][0]["children"][0]["children"][0]["text"],
            "中国文化",
        )
        self.assertEqual(
            updated_page["children"][1]["children"][0]["children"][0]["text"],
            "传统与现代的对话",
        )
        self.assertEqual(
            updated_page["children"][2]["children"][0]["children"][0]["text"],
            "从礼乐制度、审美观念和日常生活三个角度展开",
        )

    async def test_modify_slide_json_falls_back_to_llm_for_unmatched_instruction(self):
        page = _make_sample_page()
        llm_page = _make_sample_page()
        llm_page["children"][2]["children"][0]["children"][0]["text"] = "LLM fallback version"
        pptx_obj = {"width": 960, "height": 540, "pages": [page]}

        with patch(
            "app.services.ppt.nodes._get_llm_client",
            return_value=_make_fake_llm_client(llm_page),
        ) as mocked_client:
            updated_page = await modify_slide_json(
                instruction="把第二段精简一点并加个例子",
                pptx_obj=pptx_obj,
                slide_index=0,
            )

        mocked_client.assert_called_once()
        self.assertEqual(
            updated_page["children"][2]["children"][0]["children"][0]["text"],
            "LLM fallback version",
        )


if __name__ == "__main__":
    unittest.main()
