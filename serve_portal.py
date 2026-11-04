"""Run the local React/Django portal. Keep this terminal open while scanning."""
import argparse,os,socket,sys,threading,webbrowser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
for name in ('vendor','web-vendor'):
    if (ROOT/name).is_dir():sys.path.insert(0,str(ROOT/name))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','webapp.settings')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8000);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    if not (ROOT/'frontend/dist/index.html').is_file():raise SystemExit('Build the React interface first: cd frontend, npm ci, npm run build. Or run Setup Windows.bat.')
    with socket.socket() as probe:
        try:probe.bind(('127.0.0.1',args.port))
        except OSError:raise SystemExit(f'Port {args.port} is busy. Stop the existing portal or choose --port 8001.')
    import django
    django.setup()
    from django.core.management import call_command
    call_command('migrate',interactive=False,verbosity=0)
    from portal.worker import recover_interrupted_jobs
    recover_interrupted_jobs()
    url=f'http://127.0.0.1:{args.port}'
    print(f'AI File Inspector: {url}\nKeep this window open. Ctrl+C stops the portal.',flush=True)
    if not args.no_browser:
        timer=threading.Timer(2,lambda:webbrowser.open(url));timer.daemon=True;timer.start()
    call_command('runserver',f'127.0.0.1:{args.port}',use_reloader=False)
if __name__=='__main__':main()
