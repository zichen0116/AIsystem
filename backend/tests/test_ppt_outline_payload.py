import unittest

from app.services.ppt.outline_payload import (
    build_page_image_markdown,
    markdown_to_outline_payload,
    payload_to_docmee_markdown,
)


class OutlinePayloadTests(unittest.TestCase):
    def test_payload_to_docmee_markdown_includes_selected_image_with_docmee_syntax(self):
        payload = {
            "title": "中国传统文化",
            "sections": [
                {
                    "title": "章节一",
                    "pages": [
                        {
                            "title": "页面一",
                            "subtitle": "副标题",
                            "blocks": [
                                {"title": "段落标题一", "content": ["段落文本内容", "段落文本内容2"]},
                            ],
                            "image_candidates": [
                                {"id": "img-a", "url": "https://img.example.com/a.png"},
                                {"id": "img-b", "url": "https://img.example.com/b.png"},
                            ],
                            "selected_image_id": "img-b",
                        }
                    ],
                }
            ],
        }

        markdown = payload_to_docmee_markdown(payload)

        self.assertIn("# 中国传统文化", markdown)
        self.assertIn("## 章节一", markdown)
        self.assertIn("### 页面一", markdown)
        self.assertIn("#### 段落标题一", markdown)
        self.assertIn("- 段落文本内容", markdown)
        self.assertIn("![配图2](https://img.example.com/b.png)", markdown)

    def test_payload_to_docmee_markdown_omits_image_when_user_does_not_select_one(self):
        payload = {
            "title": "中国传统文化",
            "sections": [
                {
                    "title": "章节一",
                    "pages": [
                        {
                            "title": "页面一",
                            "blocks": [{"title": "段落标题一", "content": "段落文本内容"}],
                            "image_candidates": [
                                {"id": "img-a", "url": "https://img.example.com/a.png"},
                                {"id": "img-b", "url": "https://img.example.com/b.png"},
                            ],
                            "selected_image_id": None,
                        }
                    ],
                }
            ],
        }

        markdown = payload_to_docmee_markdown(payload)

        self.assertNotIn("![配图", markdown)

    def test_build_page_image_markdown_returns_empty_for_invalid_selection(self):
        page = {
            "image_candidates": [{"id": "img-a", "url": "https://img.example.com/a.png"}],
            "selected_image_id": "missing",
        }

        self.assertEqual(build_page_image_markdown(page), "")

    def test_markdown_to_outline_payload_supports_flat_page_markdown(self):
        markdown = """# 中国传统文化

## 第 1 页：封面与课程信息
- 主标题：中国传统文化
- 适用对象：本科生

## 第 2 页：教学目标与课程导入
- 核心目标：建立整体认识
- 重点聚焦：中国建筑与瓷器文化
"""

        payload = markdown_to_outline_payload(
            markdown,
            image_urls={
                "0": ["https://img.example.com/cover-a.png", "https://img.example.com/cover-b.png"],
                "1": ["https://img.example.com/goal-a.png", "https://img.example.com/goal-b.png"],
            },
        )

        self.assertEqual(payload["title"], "中国传统文化")
        self.assertEqual(len(payload["sections"]), 1)
        self.assertEqual(payload["sections"][0]["title"], "内容大纲")
        self.assertEqual(len(payload["sections"][0]["pages"]), 2)

        first_page = payload["sections"][0]["pages"][0]
        self.assertEqual(first_page["title"], "第 1 页：封面与课程信息")
        self.assertEqual(len(first_page["blocks"]), 1)
        self.assertEqual(
            first_page["blocks"][0]["content"],
            ["主标题：中国传统文化", "适用对象：本科生"],
        )
        self.assertEqual(len(first_page["image_candidates"]), 2)

    def test_payload_to_docmee_markdown_keeps_page_content_for_flat_payload(self):
        payload = {
            "title": "中国传统文化",
            "sections": [
                {
                    "title": "内容大纲",
                    "pages": [
                        {
                            "title": "第 1 页：封面与课程信息",
                            "blocks": [{"title": "", "content": ["主标题：中国传统文化"]}],
                            "image_candidates": [
                                {"id": "img-a", "url": "https://img.example.com/a.png"},
                                {"id": "img-b", "url": "https://img.example.com/b.png"},
                            ],
                            "selected_image_id": "img-a",
                        }
                    ],
                }
            ],
        }

        markdown = payload_to_docmee_markdown(payload)

        self.assertIn("## 内容大纲", markdown)
        self.assertIn("### 第 1 页：封面与课程信息", markdown)
        self.assertIn("- 主标题：中国传统文化", markdown)
        self.assertIn("![配图1](https://img.example.com/a.png)", markdown)

    def test_markdown_to_outline_payload_handles_legacy_shifted_image_indexes(self):
        markdown = """# 中国传统文化

## 第 1 页：封面与课程信息
- 主标题：中国传统文化

## 第 2 页：教学目标与课程导入
- 核心目标：建立整体认识
"""

        payload = markdown_to_outline_payload(
            markdown,
            image_urls={
                "0": ["https://img.example.com/title-a.png", "https://img.example.com/title-b.png"],
                "1": ["https://img.example.com/page1-a.png", "https://img.example.com/page1-b.png"],
                "2": ["https://img.example.com/page2-a.png", "https://img.example.com/page2-b.png"],
            },
        )

        pages = payload["sections"][0]["pages"]
        self.assertEqual(pages[0]["image_candidates"][0]["url"], "https://img.example.com/page1-a.png")
        self.assertEqual(pages[1]["image_candidates"][0]["url"], "https://img.example.com/page2-a.png")


if __name__ == "__main__":
    unittest.main()
