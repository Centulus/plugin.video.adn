import pytest

from resources.lib.kodi import i18n


@pytest.fixture
def menu_language(monkeypatch):
    def use(value):
        monkeypatch.setattr(i18n.xbmcaddon, "Addon", lambda: type("A", (), {"getSetting": lambda *_: value})())
        i18n._folder.cache_clear()
    yield use
    i18n._folder.cache_clear()


def test_french_by_default(menu_language):
    menu_language("")
    assert i18n.tr(i18n.L.RESUME) == "Reprendre"


def test_english_when_chosen(menu_language):
    menu_language("en")
    assert i18n.tr(i18n.L.RESUME) == "Resume"


@pytest.mark.parametrize("folder", sorted(set(i18n._FOLDERS.values())))
def test_every_language_translates_every_id(folder):
    ids = {value for name, value in vars(i18n.L).items() if not name.startswith("_")}
    missing = ids - set(i18n._strings(folder))
    assert not missing, missing
