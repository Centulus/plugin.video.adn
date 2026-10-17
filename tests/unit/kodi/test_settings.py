from resources.lib.kodi import settings as settings_module


class KodiAddon:
    """Like Kodi: an instance copies the settings file once, and saves its whole copy on any write."""

    file = {}

    def __init__(self):
        self.values = dict(self.file)

    def getSetting(self, key):
        return self.values.get(key, "")

    def setSetting(self, key, value):
        self.values[key] = value
        KodiAddon.file = dict(self.values)


def make(monkeypatch, **values):
    KodiAddon.file = dict(values)
    monkeypatch.setattr(settings_module.xbmcaddon, "Addon", KodiAddon)
    return settings_module.Settings()


def test_language_and_quality_follow_the_profile_by_default(monkeypatch):
    store = make(monkeypatch, preferred_quality="fhd")
    assert (store.language, store.quality) == (settings_module.FOLLOW, "fhd")


def test_sign_out_forgets_profile_but_keeps_username(monkeypatch):
    store = make(monkeypatch, adn_username="centulus", profile_id="2", access_token="A")
    store.clear_account()
    assert store.username == "centulus"
    assert (store.access_token, store.profile_id) == ("", "1")


def test_a_write_never_puts_back_a_value_changed_meanwhile(monkeypatch):
    store = make(monkeypatch, preferred_language="vostf", access_token="old")
    KodiAddon.file["preferred_language"] = "follow"  # the user changes it in the settings dialog
    store.access_token = "refreshed"  # a long playback refreshes its token later
    assert KodiAddon.file == {"preferred_language": "follow", "access_token": "refreshed"}
