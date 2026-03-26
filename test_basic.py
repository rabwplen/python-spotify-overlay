import json
from pathlib import Path

import utils


def test_file_path_returns_existing_project_file():
    path = utils.file_path("auth_success.html")
    assert Path(path).exists()


def test_get_data_path_ends_with_filename():
    path = utils.get_data_path("settings.json")
    assert path.endswith("settings.json")


# def test_save_and_load_settings_roundtrip(tmp_path, monkeypatch):
#     monkeypatch.setattr(utils, "get_data_path", lambda filename: str(tmp_path / filename))

#     data = {"opacity": 0.85, "draggable": True, "click_through": False}
#     utils.save_settings(data)

#     loaded = utils.load_settings()
#     assert loaded == data