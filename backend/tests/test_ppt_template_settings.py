from app.generators.ppt.template_settings import merge_project_settings


def test_merge_project_settings_clears_stale_oss_key_when_switching_to_non_oss_template():
    merged = merge_project_settings(
        {
            "template_image_url": "https://bucket.example.com/ppt/templates/old.png",
            "template_oss_key": "ppt/templates/demo/old.png",
            "aspect_ratio": "16:9",
        },
        {
            "template_image_url": "/templates/template_glass.png",
        },
    )

    assert merged["template_image_url"] == "/templates/template_glass.png"
    assert "template_oss_key" not in merged
    assert merged["aspect_ratio"] == "16:9"


def test_merge_project_settings_keeps_explicit_oss_key_for_uploaded_project_template():
    merged = merge_project_settings(
        {"aspect_ratio": "16:9"},
        {
            "template_image_url": "https://bucket.example.com/ppt/templates/new.png",
            "template_oss_key": "ppt/templates/demo/new.png",
        },
    )

    assert merged["template_image_url"] == "https://bucket.example.com/ppt/templates/new.png"
    assert merged["template_oss_key"] == "ppt/templates/demo/new.png"
