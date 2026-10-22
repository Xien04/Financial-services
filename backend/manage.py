#!/usr/bin/env python
"""Django command entry point; configuration arrives from the environment."""

import os
import sys

from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    execute_from_command_line(sys.argv)
