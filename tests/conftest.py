"""Makes resources.lib importable outside Kodi, with Kodi's modules faked."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

for _name in ("xbmc", "xbmcgui", "xbmcplugin", "xbmcaddon", "xbmcvfs"):
    sys.modules[_name] = MagicMock()


class _Player:
    """A real class to derive from, so player subclasses keep their own methods."""


sys.modules["xbmc"].Player = _Player
