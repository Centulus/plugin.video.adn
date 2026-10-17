"""The objects of one plugin invocation (Kodi starts a new process per action)."""
from __future__ import annotations

from .adn.api import AdnApi
from .adn.auth import AuthManager
from .adn.http import AdnHttpClient
from .kodi.settings import Settings
from .routing import Router


class Context:
    def __init__(self, argv: list) -> None:
        self.settings = Settings()
        self.http = AdnHttpClient()
        self.auth = AuthManager(self.http, self.settings)
        self.api = AdnApi(self.http, self.settings)
        self.router = Router(base_url=argv[0], handle=int(argv[1]))
        self.query = argv[2]
