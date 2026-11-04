import hashlib
import gc
import importlib
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, PngImagePlugin
from docx import Document
from pypdf import PdfWriter
from reportlab.pdfgen import canvas
import inspector as app
from report_view import render_report, file_status


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.root = Path(self.tmp.name)
        self.assets = self.root/'assets'
        self.assets.mkdir()

    def tearDown(self):
        assert Path(self.tmp.name).resolve().parent == Path(__file__).resolve().parent
        self.tmp.cleanup()

    def scan(self, path):
        return app.inspect_file(path, self.assets, [0])

    def textfile(self, name='test.txt', text='Ordinary text.'):
        path = self.root/name
        path.write_text(text, encoding='utf-8')
        return path

    def picture(self, name='sample.png', mode='RGB', size=(100,100)):
        path = self.root/name
        Image.new(mode, size).save(path)
        return path

    def test_plain_text(self):
        result = self.scan(self.textfile())
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['text']['unusual_character_count'], 0)

    def test_hidden_count_positions_and_line_separators(self):
        result = app.text_scan('A\u200bB\nC\u2028D\u2029E\x00')
        self.assertEqual(result['unusual_character_count'], 4)
        self.assertEqual(result['unusual_characters_first_100'][0]['column'], 2)
        self.assertEqual(result['unusual_characters_first_100'][1]['line'], 2)

    def test_tabs_and_windows_newlines_not_flagged(self):
        self.assertEqual(app.text_scan('A\tB\r\nC')['unusual_character_count'], 0)

    def test_mixed_alphabet(self):
        self.assertEqual(app.text_scan('p\u0430ypal')['mixed_alphabet_word_count'], 1)
        self.assertEqual(app.text_scan('नमस्ते العربية Ελληνικά')['mixed_alphabet_word_count'], 0)

    def test_emoji_and_joiner_described_without_verdict(self):
        result = app.text_scan('👩\u200d💻')
        self.assertEqual(result['unusual_character_count'], 1)
        self.assertNotIn('ai_pattern_score', result['ai_detection'])

    def test_finding_limit_keeps_total(self):
        result = app.text_scan('\u200b'*150)
        self.assertEqual(result['unusual_character_count'], 150)
        self.assertEqual(len(result['unusual_characters_first_100']), 100)

    def test_all_text_extensions(self):
        for ext in app.TEXT:
            with self.subTest(ext=ext):
                self.assertEqual(self.scan(self.textfile('text'+ext))['status'], 'complete')

    def test_utf_encodings(self):
        for encoding in ('utf-8-sig','utf-16','utf-32'):
            with self.subTest(encoding=encoding):
                p = self.root/'encoded.txt'
                p.write_bytes('Hello\u200b'.encode(encoding))
                r = self.scan(p)
                self.assertEqual(r['status'], 'complete')
                self.assertGreaterEqual(r['text']['unusual_character_count'], 1)

    def test_bad_encoding_is_partial(self):
        p = self.root/'bad.txt'
        p.write_bytes(b'hello\xff')
        self.assertEqual(self.scan(p)['status'], 'partial')

    def test_empty_text(self):
        self.assertEqual(self.scan(self.textfile(text=''))['text']['characters'], 0)

    def test_all_image_extensions(self):
        for ext in app.IMAGES:
            with self.subTest(ext=ext):
                r = self.scan(self.picture('image'+ext))
                self.assertEqual(len(r['images'][0]['visuals']), 2)

    def test_image_modes(self):
        for mode in ('L', 'RGBA', 'P'):
            with self.subTest(mode=mode):
                self.assertEqual(self.scan(self.picture(mode+'.png', mode))['status'], 'complete')

    def test_small_image(self):
        self.assertEqual(self.scan(self.picture(size=(8,8)))['images'][0]['visuals'], [])

    def test_large_image_reduced(self):
        r = self.scan(self.picture(size=(2000,100)))
        self.assertEqual(r['images'][0]['analysis_dimensions'][0], 1600)

    def test_multiframe_is_partial(self):
        p = self.root/'multi.tiff'
        Image.new('RGB',(80,80)).save(p, save_all=True, append_images=[Image.new('RGB',(80,80),'red')])
        self.assertEqual(self.scan(p)['status'], 'partial')

    def test_metadata_hint_not_body_text(self):
        self.assertNotIn('metadata_keyword_hints', self.scan(self.textfile(text='Midjourney SynthID')))
        p = self.root/'meta.png'
        info = PngImagePlugin.PngInfo()
        info.add_text('Software', 'ComfyUI')
        Image.new('RGB',(80,80)).save(p, pnginfo=info)
        self.assertIn('ComfyUI', self.scan(p)['images'][0]['metadata_keyword_hints'])

    def test_corrupt_image_fails(self):
        p = self.root/'bad.png'
        p.write_bytes(b'no picture')
        with self.assertRaisesRegex(ValueError, 'picture could not'):
            self.scan(p)

    def test_word_text_tables_headers_and_images(self):
        p = self.root/'word.docx'
        doc = Document()
        doc.add_paragraph('Text\u200b')
        doc.add_table(rows=1, cols=1).cell(0,0).text = 'Table\u200b'
        doc.sections[0].header.paragraphs[0].text = 'Header\u200b'
        doc.add_section()
        doc.add_picture(str(self.picture()))
        doc.save(p)
        r = self.scan(p)
        self.assertEqual(r['text']['unusual_character_count'], 3)
        self.assertEqual(len(r['images']), 1)

    def test_pdf_text_image(self):
        p = self.root/'document.pdf'
        c = canvas.Canvas(str(p))
        c.drawString(30,500,'A readable PDF sentence.')
        c.drawImage(str(self.picture()),30,300,width=100,height=100)
        c.save()
        r = self.scan(p)
        self.assertGreater(r['text']['characters'], 10)
        self.assertEqual(len(r['images']), 1)
        self.assertEqual(r['status'], 'complete')

    def test_image_only_pdf_partial(self):
        p = self.root/'scan.pdf'
        c = canvas.Canvas(str(p))
        c.drawImage(str(self.picture()),30,300,width=100,height=100)
        c.save()
        self.assertEqual(self.scan(p)['status'], 'partial')

    def test_mixed_scanned_and_text_pdf_partial(self):
        p = self.root/'mixed.pdf'
        c = canvas.Canvas(str(p))
        c.drawString(30,500,'Readable text on page one.')
        c.showPage()
        c.drawImage(str(self.picture()),30,300,width=100,height=100)
        c.save()
        r = self.scan(p)
        self.assertEqual(r['status'], 'partial')
        self.assertTrue(any('Page 2' in x for x in r['issues']))

    def test_locked_pdf(self):
        p = self.root/'locked.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=100,height=100)
        writer.encrypt('secret')
        writer.write(p)
        with self.assertRaisesRegex(ValueError, 'Password'):
            self.scan(p)

    def test_page_limit(self):
        p = self.root/'long.pdf'
        writer = PdfWriter()
        for _ in range(301):
            writer.add_blank_page(width=20,height=20)
        writer.write(p)
        r = self.scan(p)
        self.assertTrue(any('300' in x for x in r['issues']))

    def test_file_size_limit(self):
        with patch.object(app, 'MAX_BYTES', 2):
            with self.assertRaisesRegex(ValueError, '100 MB'):
                self.scan(self.textfile())

    def test_missing_and_unsupported(self):
        for p in (self.root/'missing.txt', self.textfile('unsupported.exe')):
            with self.subTest(path=p), self.assertRaises(Exception):
                self.scan(p)

    def test_c2pa_absent(self):
        with patch.object(app.shutil, 'which', return_value=None):
            self.assertIn('Not checked', app.credentials(self.root/'x.png')['status'])

    def test_c2pa_external_success_failure_timeout(self):
        with patch.object(app.shutil, 'which', return_value='c2patool'):
            for code in (0,1):
                with patch.object(app.subprocess, 'run', return_value=subprocess.CompletedProcess([],code,b'{"validation_status":[]}',b'')):
                    self.assertEqual(app.credentials(self.root/'x.png')['exit_code'],code)
            with patch.object(app.subprocess, 'run', side_effect=subprocess.TimeoutExpired('c2patool',40)):
                self.assertIn('error',app.credentials(self.root/'x.png'))

    def test_folder_skips_generated_reports_not_user_reports(self):
        legitimate = self.root/'reports'
        legitimate.mkdir()
        (legitimate/'notes.txt').write_text('keep')
        generated = self.root/'old-run'
        generated.mkdir()
        (generated/'report.json').write_text('{}')
        (generated/'report.html').write_text('report')
        self.assertEqual(app.collect([self.root]),[legitimate/'notes.txt'])

    def test_duplicate_selection(self):
        p = self.textfile()
        self.assertEqual(app.collect([p,p]),[p])

    def test_mixed_batch_preserves_originals(self):
        paths = [self.textfile(), self.picture(), self.textfile('broken.pdf', 'not a pdf')]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        report = app.make_report(paths,self.root/'report')
        results = json.loads(report.with_suffix('.json').read_text(encoding='utf-8'))['files']
        self.assertEqual([file_status(r)[0] for r in results],['complete','complete','failed'])
        self.assertEqual(before,[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])

    def test_does_not_overwrite_existing_output(self):
        with self.assertRaises(FileExistsError):
            app.make_report([self.textfile()],self.assets)

    def test_html_escapes_file_content(self):
        payload = '<script>alert(1)</script>'
        r = {'file':payload+'.txt','error':payload}
        rendered = render_report({'files':[r]})
        self.assertNotIn('<script>',rendered)
        self.assertIn('&lt;script&gt;',rendered)

    def test_image_paths_cannot_escape_assets(self):
        r = {'file':'test.png','images':[{'visuals':[{'file':'../../secret.png'}]}]}
        self.assertNotIn('<img ',render_report({'files':[r]}))

    def test_details_closed_by_default(self):
        p = self.picture()
        report = app.make_report([p],self.root/'report')
        text = report.read_text(encoding='utf-8')
        self.assertIn('class="image-details"',text)
        self.assertNotIn('<details open',text)
        self.assertNotIn('AI PROBABILITY',text)


class DesktopTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop_ui import InspectorApp
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.root = tk.Tk()
        self.ui = InspectorApp(self.root, app.make_report, app.collect, app.SUPPORTED, Path(self.tmp.name)/'reports')
        self.root.update()

    def tearDown(self):
        if not self.ui.closed:
            self.ui.close()
        del self.ui
        del self.root
        gc.collect()
        assert Path(self.tmp.name).resolve().parent == Path(__file__).resolve().parent
        self.tmp.cleanup()

    def pump(self):
        deadline = time.monotonic()+10
        while self.ui.busy and time.monotonic()<deadline:
            self.root.update()
            time.sleep(.02)
        self.root.update()
        self.assertFalse(self.ui.busy)

    def test_layout_fits_minimum_window(self):
        self.root.geometry('720x540')
        self.root.update()
        for widget in (self.ui.files_button,self.ui.folder_button,self.ui.report_button,self.ui.progress):
            self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())

    def test_cancel_picker_does_nothing(self):
        with patch('desktop_ui.filedialog.askopenfilenames',return_value=()):
            self.ui.choose_files()
        self.assertFalse(self.ui.busy)

    def test_empty_folder_recovers(self):
        self.ui.start([self.tmp.name])
        self.pump()
        self.assertIn('No supported',self.ui.status.get())
        self.assertFalse(self.ui.files_button.instate(['disabled']))

    def test_real_scan_and_open_latest(self):
        p = Path(self.tmp.name)/'test.txt'
        p.write_text('Hello')
        with patch('desktop_ui.webbrowser.open',return_value=True) as opener:
            self.ui.start([p])
            self.assertTrue(self.ui.files_button.instate(['disabled']))
            self.pump()
            self.assertTrue(self.ui.latest.exists())
            self.ui.report_button.invoke()
            self.assertEqual(opener.call_count,2)

    def test_worker_failure_recovers(self):
        self.ui.collect = lambda _: (_ for _ in ()).throw(OSError('test failure'))
        with patch('desktop_ui.messagebox.showerror') as error:
            self.ui.start(['x'])
            self.pump()
            error.assert_called_once()
        self.assertFalse(self.ui.files_button.instate(['disabled']))

    def test_browser_failure_shows_saved_path(self):
        self.ui.latest = Path(self.tmp.name)/'report.html'
        self.ui.latest.write_text('test')
        with patch('desktop_ui.webbrowser.open',return_value=False):
            self.ui.open_report()
        self.assertIn('Open this file',self.ui.status.get())

    def test_missing_report(self):
        self.ui.latest = Path(self.tmp.name)/'missing.html'
        self.ui.open_report()
        self.assertIn('moved or was deleted',self.ui.status.get())


if __name__ == '__main__':
    unittest.main(verbosity=2)

