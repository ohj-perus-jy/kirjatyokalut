"""TIM-sivujen luettelo linkkitarkistukselle (linkit/tim_sivut.py) ilman
verkkoa: getItems korvataan sanakirjalla."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "linkit"))

import tim_sivut  # noqa: E402  (polku asetettu yllä)

TREE = {
    "k": [{"path": "k/koti", "isFolder": False},
          {"path": "k/demot", "isFolder": True},
          {"path": "k/moniste", "isFolder": False}],
    "k/demot": [{"path": "k/demot/demo1", "isFolder": False}],
    "j": [{"path": "j/wiki", "isFolder": False}],
}


def test_pages_walk_subfolders_and_leave_out_skipped():
    config = {"linkit": {"tim_kansiot": ["k", "j"], "tim_pois": ["k/moniste"]}}
    assert tim_sivut.pages(config, TREE.__getitem__) == [
        "https://tim.jyu.fi/view/k/koti",
        "https://tim.jyu.fi/view/k/demot/demo1",
        "https://tim.jyu.fi/view/j/wiki",
    ]


def test_main_fails_without_folders(tmp_path, capsys):
    config = tmp_path / "kirja.toml"
    config.write_text('nimi = "koe"\n', encoding="utf-8")
    assert tim_sivut.main(["tim_sivut.py", str(config)]) == 1
    assert "tim_kansiot" in capsys.readouterr().err
