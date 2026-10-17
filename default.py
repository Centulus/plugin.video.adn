"""Kodi entry point."""
import sys

from resources.lib import routes
from resources.lib.context import Context

if __name__ == "__main__":
    routes.run(Context(sys.argv))
