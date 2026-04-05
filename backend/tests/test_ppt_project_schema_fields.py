import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "generators" / "ppt" / "banana_schemas.py"
SPEC = importlib.util.spec_from_file_location("banana_schemas_for_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

PPTProjectCreate = MODULE.PPTProjectCreate
ProjectSettingsUpdate = MODULE.ProjectSettingsUpdate


def test_project_create_accepts_long_template_style_with_short_theme():
    model = PPTProjectCreate(
        title="demo",
        creation_type="dialog",
        theme="Eco",
        template_style="A" * 500,
        settings={"template_style": "B" * 600},
    )

    assert model.theme == "Eco"
    assert model.template_style == "A" * 500


def test_project_create_migrates_long_theme_to_template_style():
    theme = "x" * 80
    model = PPTProjectCreate(
        title="demo",
        creation_type="dialog",
        theme=theme,
    )

    assert model.theme == theme[:50]
    assert model.template_style == theme


def test_project_settings_update_accepts_template_style():
    model = ProjectSettingsUpdate(template_style="Detailed style guidance")
    assert model.template_style == "Detailed style guidance"


def test_project_settings_update_migrates_long_theme_to_template_style():
    theme = "y" * 120
    model = ProjectSettingsUpdate(theme=theme)

    assert model.theme == theme[:50]
    assert model.template_style == theme
