from __future__ import annotations


def merge_project_settings(existing_settings: dict | None, update_data: dict | None) -> dict:
    """Merge project settings while keeping template source fields consistent."""
    merged = dict(existing_settings or {})
    updates = dict(update_data or {})

    for key, value in updates.items():
        if key in {"template_image_url", "template_oss_key"}:
            continue
        merged[key] = value

    if "template_image_url" in updates:
        template_image_url = str(updates.get("template_image_url") or "").strip()
        if template_image_url:
            merged["template_image_url"] = updates["template_image_url"]
        else:
            merged.pop("template_image_url", None)

        if "template_oss_key" in updates:
            template_oss_key = str(updates.get("template_oss_key") or "").strip()
            if template_oss_key:
                merged["template_oss_key"] = updates["template_oss_key"]
            else:
                merged.pop("template_oss_key", None)
        else:
            merged.pop("template_oss_key", None)
    elif "template_oss_key" in updates:
        template_oss_key = str(updates.get("template_oss_key") or "").strip()
        if template_oss_key:
            merged["template_oss_key"] = updates["template_oss_key"]
        else:
            merged.pop("template_oss_key", None)

    return merged
