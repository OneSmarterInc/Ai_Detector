"""Compatibility entry point: portal by default; existing CLI arguments still work."""
import sys,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
for name in ('vendor','web-vendor'):
    if (ROOT/name).is_dir():sys.path.insert(0,str(ROOT/name))
if sys.argv[1:]==['--check']:
    import django,PIL,numpy,pypdf,docx,lxml,onnxruntime,tokenizers,langdetect
    import ai_detector
    ai_detector.get_engine()
    assert (ROOT/'frontend/dist/index.html').is_file(),'Build React with Setup Windows.bat'
    print('PASS: portal dependencies, React build and Gradient model are available.')
elif not sys.argv[1:]:
    from serve_portal import main
    main()
else:
    runpy.run_path(str(ROOT/'inspector.py'),run_name='__main__')
