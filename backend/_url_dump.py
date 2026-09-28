import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.urls import get_resolver


def walk(resolver, prefix=""):
    for entry in resolver.url_patterns:
        text = prefix + str(entry.pattern)
        if hasattr(entry, "url_patterns"):
            walk(entry, text)
        else:
            print(text)


walk(get_resolver())
