"""Local file inspection. Findings are observations, never AI authorship verdicts."""
from __future__ import annotations
import argparse
import collections
import datetime
import html
import io
import json
import math
import re
import shutil
import subprocess
import threading
import queue
import os
import unicodedata
import webbrowser
import zipfile
from pathlib import Path

TEXT = {'.txt', '.md', '.csv', '.json', '.py', '.html', '.xml', '.tex', '.log'}
IMAGES = {'.png', '.jpg', '.jpeg', '.webp', '.tif', '.tiff', '.bmp'}
SUPPORTED = TEXT | IMAGES | {'.pdf', '.docx'}
MAX_BYTES = 100 * 1024 * 1024
LIMIT = 100
TOOLS = re.compile(r'SynthID|DALL-E|Midjourney|Stable Diffusion|Firefly|Imagen|ComfyUI|Automatic1111|InvokeAI|trainedAlgorithmicMedia|compositeSynthetic', re.I)
NOTICE = ('This report shows file observations, not proof of AI authorship. Hidden characters, '
          'writing style, metadata keywords, and image patterns can have ordinary explanations. '
          'No findings does not prove human authorship. This tool does not detect SynthID or other proprietary watermarks.')

def text_scan(text, detect_ai=True):
    hits, mixed, scripts = [], [], collections.Counter()
    hidden_count = mixed_count = 0
    for line_no, line in enumerate(text.split('\n'), 1):
        for col, ch in enumerate(line, 1):
            cp, category = ord(ch), unicodedata.category(ch)
            if category in ('Cf', 'Co', 'Zl', 'Zp') or (category == 'Cc' and ch not in '\r\t') or (category == 'Zs' and ch != ' ') or 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF:
                hidden_count += 1
                if len(hits) < LIMIT:
                    hits.append({'line': line_no, 'column': col, 'code': f'U+{cp:04X}', 'name': unicodedata.name(ch, 'UNNAMED'), 'context': ascii(line[max(0, col-12):col+12])})
        for match in re.finditer(r'[^\W\d_]+', line):
            found = set()
            for ch in match.group():
                name = unicodedata.name(ch, '')
                for script in ('LATIN', 'CYRILLIC', 'GREEK', 'ARABIC', 'HEBREW', 'DEVANAGARI', 'ARMENIAN'):
                    if name.startswith(script):
                        found.add(script)
                        scripts[script] += 1
                        break
            if 'LATIN' in found and len(found) > 1:
                mixed_count += 1
                if len(mixed) < LIMIT:
                    mixed.append({'line': line_no, 'column': match.start()+1, 'word': match.group(), 'scripts': sorted(found)})
    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text.lower())
    sentences = [len(re.findall(r'\b\w+\b', s)) for s in re.split(r'[.!?]+(?:\s+|$)', text) if s.strip()]
    stats = {'note': 'Descriptive only. English-oriented word counts and simple sentence splitting; unsuitable for authorship judgments.'}
    if words:
        counts = collections.Counter(words)
        stats.update(english_word_count=len(words), unique_word_ratio=round(len(counts)/len(words), 3), word_entropy_bits=round(-sum((n/len(words))*math.log2(n/len(words)) for n in counts.values()), 3))
    if len(sentences) >= 4:
        avg = sum(sentences)/len(sentences)
        stats['sentence_length_variation'] = round(math.sqrt(sum((n-avg)**2 for n in sentences)/len(sentences))/max(avg, 1), 3)
    from ai_detector import analyze
    ai_result = analyze(text, enabled=detect_ai)
    return {'characters': len(text), 'unusual_character_count': hidden_count, 'unusual_characters_first_100': hits,
            'mixed_alphabet_word_count': mixed_count, 'mixed_alphabet_words_first_100': mixed, 'writing_statistics': stats,
            'ai_detection': ai_result,
            'interpretation': 'These characters and alphabet combinations may be normal formatting or legitimate language use.'}

def keyword_hints(metadata):
    return sorted(set(m.group() for m in TOOLS.finditer(json.dumps(metadata, ensure_ascii=False))))

def image_scan(data, label, assets, number):
    import numpy as np
    from PIL import Image, ImageChops, ImageEnhance, ImageOps, ExifTags
    result = {'source': label, 'visuals': []}
    with Image.open(io.BytesIO(data)) as original:
        if original.width * original.height > 40_000_000:
            raise ValueError('Image exceeds the 40 megapixel inspection limit.')
        result['original_dimensions'] = list(original.size)
        metadata = {str(k): str(v)[:3000] for k, v in original.info.items() if k not in ('icc_profile', 'exif')}
        metadata['exif'] = {ExifTags.TAGS.get(k, str(k)): str(v)[:1000] for k, v in original.getexif().items()}
        result['metadata'] = metadata
        result['metadata_keyword_hints'] = keyword_hints(metadata)
        if getattr(original, 'n_frames', 1) > 1:
            result['frame_note'] = 'This file has several frames or pages. Only the first image was checked.'
        rgba = ImageOps.exif_transpose(original).convert('RGBA')
        img = Image.new('RGBA', rgba.size, 'white')
        img.alpha_composite(rgba)
        img = img.convert('RGB')
        if max(img.size) > 1600:
            img.thumbnail((1600, 1600))
            result['analysis_note'] = 'Reduced to at most 1600 pixels per side for exploratory analysis; resizing changes the measurements.'
        result['analysis_dimensions'] = list(img.size)
        if min(img.size) < 64:
            result['analysis_note'] = 'Image too small for useful pattern visualizations.'
            return result
        gray = np.asarray(img.convert('L'), dtype=float)
        window = np.hanning(gray.shape[0])[:, None] * np.hanning(gray.shape[1])[None, :]
        mag = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2((gray-gray.mean()) * window))))
        span = float(np.ptp(mag))
        spectrum = ((mag-mag.min()) / max(span, 1e-9) * 255).astype('uint8')
        fft_path = assets / f'image_{number}_patterns.png'
        Image.fromarray(spectrum).save(fft_path)
        result['visuals'].append({'file': 'assets/'+fft_path.name, 'caption': 'FFT: repeating image patterns. Bright structures do not establish an AI watermark.'})
        buffer = io.BytesIO()
        img.save(buffer, 'JPEG', quality=90)
        buffer.seek(0)
        with Image.open(buffer) as compressed:
            diff = ImageChops.difference(img, compressed.convert('RGB'))
        arr = np.asarray(diff, dtype=float)
        scale = min(30, 255/max(float(arr.max()), 1))
        ela_path = assets / f'image_{number}_compression.png'
        ImageEnhance.Brightness(diff).enhance(scale).save(ela_path)
        result['mean_recompression_difference'] = round(float(arr.mean()), 3)
        result['visuals'].append({'file': 'assets/'+ela_path.name, 'caption': 'ELA: changes after JPEG recompression, amplified for visibility. Texture and ordinary editing also create differences.'})
    return result

def credentials(path):
    executable = shutil.which('c2patool')
    if not executable:
        return {'status': 'Not checked: optional c2patool is not installed. Metadata keyword searches do not verify signatures.'}
    try:
        proc = subprocess.run([executable, str(path)], capture_output=True, timeout=40)
        output = proc.stdout.decode('utf-8', 'replace')
        try:
            payload = json.loads(output)
        except ValueError:
            payload = output[:20000]
        return {'status': 'External c2patool result; inspect its validation status and trust information. Presence alone does not imply AI.',
                'exit_code': proc.returncode, 'report': payload, 'errors': proc.stderr.decode('utf-8', 'replace')[:4000]}
    except Exception as exc:
        return {'status': 'Credential check could not finish', 'error': str(exc)}

def inspect_file(path, assets, counter):
    result = {'file': str(path.resolve()), 'type': path.suffix.lower(), 'warnings': [], 'issues': [], 'images': []}
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('File exceeds the 100 MB limit.')
    ext = path.suffix.lower()
    def add_image(data, label):
        if len(result['images']) >= 50:
            if 'Only the first 50 embedded images were inspected.' not in result['warnings']:
                result['warnings'].append('Only the first 50 embedded images were inspected.')
            return
        counter[0] += 1
        try:
            result['images'].append(image_scan(data, label, assets, counter[0]))
        except Exception as exc:
            result['issues'].append(f'Could not read picture {label}: {exc}')
    if ext in TEXT:
        raw = path.read_bytes()
        if raw.startswith((b'\xff\xfe\x00\x00', b'\x00\x00\xfe\xff')):
            text = raw.decode('utf-32')
        elif raw.startswith((b'\xff\xfe', b'\xfe\xff')):
            text = raw.decode('utf-16')
        else:
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError:
                text = raw.decode('utf-8', 'replace')
                result['issues'].append('Some text could not be read correctly. Save a copy as UTF-8 text and check it again.')
        result['text'] = text_scan(text, detect_ai=ext not in {'.py','.json','.xml','.csv','.tex','.log'})
    elif ext in IMAGES:
        add_image(path.read_bytes(), path.name)
        if not result['images']:
            raise ValueError('The picture could not be opened. It may be damaged or too large. Try opening it in a picture viewer and saving a new copy.')
        result['content_credentials'] = credentials(path)
    elif ext == '.docx':
        import docx
        with zipfile.ZipFile(path) as archive:
            if sum(item.file_size for item in archive.infolist()) > 200*1024*1024:
                raise ValueError('Expanded Word document exceeds 200 MB.')
        doc = docx.Document(path)
        props = doc.core_properties
        result['metadata'] = {k: str(getattr(props, k, '') or '') for k in ('author', 'last_modified_by', 'created', 'modified', 'title', 'comments')}
        chunks = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                chunks.extend(cell.text for cell in row.cells)
        seen_parts = set()
        for section in doc.sections:
            for part in (section.header, section.footer):
                if str(part.part.partname) in seen_parts:
                    continue
                seen_parts.add(str(part.part.partname))
                chunks.extend(p.text for p in part.paragraphs)
        with zipfile.ZipFile(path) as archive:
            if 'docProps/app.xml' in archive.namelist():
                result['metadata']['application_properties'] = archive.read('docProps/app.xml').decode('utf-8', 'replace')[:12000]
            for name in archive.namelist():
                if name.startswith('word/media/') and Path(name).suffix.lower() in IMAGES:
                    if len(result['images']) >= 50:
                        result['warnings'].append('Only the first 50 embedded images were inspected.')
                        break
                    add_image(archive.read(name), name)
        result['text'] = text_scan('\n'.join(chunks))
        result['warnings'].append('Text boxes, tracked changes, footnotes, and some nested content may not be extracted. Line numbers refer to extracted text.')
    elif ext == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        if reader.is_encrypted and not reader.decrypt(''):
            raise ValueError('Password-protected PDF: provide an unlocked copy.')
        result['metadata'] = {str(k): str(v)[:3000] for k, v in (reader.metadata or {}).items()}
        result['page_count'] = len(reader.pages)
        chunks = []
        for idx, page in enumerate(reader.pages):
            if idx >= 300:
                result['issues'].append('Only the first 300 pages were inspected. Split this PDF into smaller files to check the remaining pages.')
                break
            page_text = None
            try:
                page_text = page.extract_text() or ''
                chunks.append(page_text)
            except Exception as exc:
                result['issues'].append(f'Text on page {idx+1} could not be read: {exc}')
            try:
                if len(result['images']) < 50:
                    for embedded in page.images:
                        if page_text is not None and not page_text.strip():
                            result['issues'].append(f'Page {idx+1} has a picture but no readable text. Any words inside it were not checked; use text recognition (OCR) if needed.')
                        add_image(embedded.data, f'Page {idx+1}: {embedded.name}')
                        if len(result['images']) >= 50:
                            result['warnings'].append('Embedded image inspection capped at 50 images.')
                            break
            except Exception as exc:
                result['issues'].append(f'Some pictures on page {idx+1} could not be read: {exc}')
        text = '\n'.join(chunks)
        result['text'] = text_scan(text)
        result['warnings'].append('PDF extraction can change or omit characters. Positions refer to extracted text. Image-only pages require OCR, which is not included.')
        if not text.strip():
            result['issues'].append('No readable text was found. If this PDF is a scan, use a text-recognition (OCR) tool first, then check the new copy.')
        result['content_credentials'] = credentials(path)
    else:
        raise ValueError('Unsupported file type.')
    if 'metadata' in result:
        result['metadata_keyword_hints'] = keyword_hints(result['metadata'])
    result['issues'].extend(w for w in result['warnings'] if '50' in w)
    result['issues'].extend(p['frame_note'] for p in result['images'] if 'frame_note' in p)
    ai_result = result.get('text',{}).get('ai_detection',{})
    if ai_result.get('status') == 'error':
        result['issues'].append('The trained AI writing detector could not run. See its message above; other checks are separate.')
    if ai_result.get('coverage') == 'sampled':
        result['issues'].append('The AI writing estimate covers selected text only, not the whole document. See the estimate for coverage.')
    result['issues'] = list(dict.fromkeys(result['issues']))
    result['status'] = 'partial' if result['issues'] else 'complete'
    return result

def make_report(paths, destination, progress=lambda msg: None):
    destination.mkdir(parents=True, exist_ok=False)
    assets = destination / 'assets'
    assets.mkdir()
    results, counter = [], [0]
    for index, path in enumerate(paths, 1):
        progress(f'Checking {index}/{len(paths)}: {path.name}')
        try:
            results.append(inspect_file(path, assets, counter))
        except Exception as exc:
            results.append({'file': str(path), 'error': str(exc), 'status': 'failed'})
    report = {'notice': NOTICE, 'created': datetime.datetime.now().astimezone().isoformat(), 'files': results}
    (destination/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    from report_view import render_report
    (destination/'report.html').write_text(render_report(report), encoding='utf-8')
    return destination/'report.html'

def collect(inputs):
    files = []
    for item in inputs:
        path = Path(item).resolve()
        if path.is_dir():
            for folder, dirs, names in os.walk(path, followlinks=False):
                here = Path(folder)
                if 'report.json' in names and 'report.html' in names:
                    dirs[:] = []
                    continue
                dirs[:] = sorted(d for d in dirs if d not in ('.git', '__pycache__') and not (here/d).is_symlink())
                files.extend(here/name for name in sorted(names) if Path(name).suffix.lower() in SUPPORTED and not (here/name).is_symlink())
        else:
            files.append(path)
    return list(dict.fromkeys(files))

def gui():
    from desktop_ui import InspectorApp
    import tkinter as tk
    root = tk.Tk()
    InspectorApp(root, make_report, collect, SUPPORTED, Path(__file__).resolve().parent/'reports')
    root.mainloop()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', help='Files or folders; omit to open the desktop window.')
    parser.add_argument('--output', type=Path, help='New directory for reports; must not already exist.')
    args = parser.parse_args()
    if args.paths:
        selected = collect(args.paths)
        if not selected:
            parser.error('No supported files found.')
        out = args.output or Path(__file__).resolve().parent/'reports'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        print(make_report(selected, out, print))
    else:
        gui()
