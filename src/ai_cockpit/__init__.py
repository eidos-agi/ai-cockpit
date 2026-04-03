"""ai-cockpit — Launch pad for all your AI cockpits."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ai-cockpit")
except PackageNotFoundError:
    __version__ = "dev"
