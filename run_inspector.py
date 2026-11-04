"""Start using the bundled Windows/Python 3.12 libraries."""
import sys,struct,runpy
from pathlib import Path
if sys.platform != 'win32' or sys.version_info[:2] != (3,12) or struct.calcsize('P') != 8:
    raise SystemExit('Use 64-bit Python 3.12 on Windows for this package.')
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'vendor'))
if sys.argv[1:] == ['--check']:
    import tkinter, PIL, numpy, pypdf, docx, lxml, onnxruntime, tokenizers, langdetect
    import ai_detector
    ai_detector.get_engine()
    print('PASS: bundled libraries and Gradient model load successfully.')
else:
    runpy.run_path(str(ROOT/'inspector.py'),run_name='__main__')
