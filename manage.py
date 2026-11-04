import sys

from scripts.bootstrap import configure

configure()
if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
