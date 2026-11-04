import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
for name in ('vendor','web-vendor'):
    if (ROOT/name).is_dir():sys.path.insert(0,str(ROOT/name))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','webapp.settings')
if __name__=='__main__':
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
