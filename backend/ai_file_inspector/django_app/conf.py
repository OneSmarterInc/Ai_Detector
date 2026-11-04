"""Host configuration. Importing the reusable app never creates local directories."""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def option(name, default=None):
    return getattr(settings, "AI_FILE_INSPECTOR", {}).get(name, default)


def data_root():
    directory = option("DATA_DIR")
    if not directory:
        raise ImproperlyConfigured(
            'Set AI_FILE_INSPECTOR["DATA_DIR"] to a private writable directory.'
        )
    return Path(directory).resolve()
