"""Plain-English, offline HTML reports. Technical sections start closed."""
import html
import json
from pathlib import Path, PurePosixPath


def esc(value):
    return html.escape(str(value), quote=True)


def file_status(result):
    if 'error' in result:
        return 'failed', 'Could not check this file'
    if result.get('issues') or result.get('status') == 'partial':
        return 'partial', 'Some checks could not finish'
    return 'complete', 'Available checks finished'


def friendly_error(raw):
    text = str(raw)
    lower = text.lower()
    if 'password' in lower or 'decrypt' in lower:
        return 'This file is locked with a password. Save an unlocked copy, then choose that copy.'
    if 'permission' in lower or 'denied' in lower:
        return 'The file could not be opened. Close it in other programs and check that you have permission to read it.'
    if 'no such file' in lower or 'cannot find' in lower:
        return 'The file could not be found. It may have moved. Choose it again from its current folder.'
    if '100 mb' in lower:
        return 'This file is larger than the 100 MB limit. Choose a smaller copy or split it into smaller files.'
    if 'unsupported' in lower:
        return 'This file type is not supported. Choose a text file, picture, Word (.docx), or PDF file.'
    if 'picture could not' in lower:
        return text
    return 'The file could not be read. Try opening it in its usual app and saving a fresh copy. The technical details are below.'


def finding(title, found, meaning):
    return f'<div class="finding"><h3>{esc(title)}</h3><div><p>{esc(found)}</p><p class="explain">{esc(meaning)}</p></div></div>'


def character_name(item):
    names = {'U+200B': 'Invisible space', 'U+00A0': 'Space that keeps words on one line',
             'U+202F': 'Narrow space that keeps words together', 'U+FEFF': 'File-start or invisible formatting mark',
             'U+200D': 'Joining mark (used in some languages and emoji)', 'U+200C': 'Letter-separation mark',
             'U+2028': 'Line-break mark', 'U+2029': 'Paragraph-break mark', 'U+0000': 'Empty control character'}
    return names.get(item.get('code'), str(item.get('name', 'Special character')).lower().capitalize())


def ai_section(result):
    text = result.get('text')
    if 'error' in result:
        return '<div class="notice"><strong>AI writing estimate: Not checked</strong><p>The file could not be read.</p></div>'
    if text is None:
        return '<div class="notice"><strong>AI writing estimate: Not applicable</strong><p>The trained detector checks English text, not pictures. Picture checks below do not detect AI authorship.</p></div>'
    detection = text.get('ai_detection')
    if not detection:
        return '<div class="notice"><strong>AI writing estimate: Not checked in this older report</strong><p>Run this file through the updated tool to use the trained text detector. Hidden-character counts alone cannot detect AI writing.</p></div>'
    if detection.get('status') != 'estimated':
        return f'<div class="notice"><strong>AI writing estimate: Not checked</strong><p>{esc(detection.get("reason", "The detector could not run."))}</p><p>This is not a human-written result.</p></div>'
    score = detection['ai_pattern_score']
    label = detection['label']
    if label == 'Leans AI-generated':
        display_label = 'Looks AI-written'
        explanation = 'The writing looks similar to AI-written examples. The tool can be wrong, so this does not prove that AI was used.'
    elif label == 'Leans human-written':
        display_label = 'Looks human-written'
        explanation = 'The writing looks similar to human-written examples. The tool can miss AI writing, so this does not prove that no AI was used.'
    elif label == 'Uncertain — passages give different signals':
        display_label = 'Not sure'
        explanation = 'Some parts look AI-written, while others look human-written. The tool cannot give a clear answer for this document. This does not prove that both a person and AI wrote it.'
    else:
        display_label = 'Not sure'
        explanation = 'The writing does not clearly match either AI-written or human-written examples. The tool cannot tell which one it is.'
    coverage = f'Checked {detection["passages_checked"]} of {detection["total_passages"]} text sections. '
    coverage += 'Some text was not checked.' if detection.get('coverage') == 'sampled' else 'All text prepared for this check was included.'
    block = f'<section class="notice ai-estimate" style="margin-top:18px"><h3>AI writing estimate: {esc(display_label)}</h3><p>{explanation}</p><p>{esc(coverage)}</p><p>This is an estimate, not proof of who wrote the text.</p></section>'
    block += '<details class="ai-passages"><summary>See scores for each text section — optional</summary>'
    block += f'<p>Model: {esc(detection["model"])}. Runs locally. English prose of at least 100 words.</p><p><strong>AI-pattern score: {score:g} / 100.</strong> This is a raw model signal, not a probability of authorship or a percentage of AI-written words. Even a score near 0 or 100 can be wrong.</p><p>Scores of 20 or lower lean human; 80 or higher lean AI. Middle scores or strongly disagreeing passages are uncertain. These cutoffs are rules for this app, not a measured accuracy guarantee.</p>'
    for note in detection.get('notes',[])[1:]:
        block += f'<p>{esc(note)}</p>'
    block += '<p>Excerpts come from cleaned, extracted text. Passage scores do not identify which individual words were written by AI.</p><div class="table-scroll"><table><thead><tr><th>Passage</th><th>AI-pattern score</th><th>Beginning of passage</th></tr></thead><tbody>'
    for passage in detection.get('passages',[]):
        block += f'<tr><td>{passage["passage_number"]}</td><td>{passage["ai_pattern_score"]:g} / 100</td><td>{esc(passage["text_excerpt"])}</td></tr>'
    block += '</tbody></table></div></details>'
    return block


def file_section(result, index):
    status, label = file_status(result)
    text = result.get('text')
    pictures = result.get('images', [])
    name = Path(result['file']).name
    content = f'<article id="file-{index}"><header class="file-heading"><h2>{esc(name)}</h2><span class="status {status}">{label}</span></header>'
    content += ai_section(result)
    if status == 'failed':
        content += f'<p class="message">{esc(friendly_error(result["error"]))}</p>'
    else:
        hidden = text.get('unusual_character_count', 0) if text else 0
        mixed = text.get('mixed_alphabet_word_count', 0) if text else 0
        hints = sorted(set(result.get('metadata_keyword_hints', []) + [h for p in pictures for h in p.get('metadata_keyword_hints', [])]))
        if status == 'partial':
            headline = 'Part of this file could not be checked. Read the notes below before using these results.'
        elif hidden or mixed or hints:
            headline = 'There are details you can review. None of these findings proves that AI was used.'
        else:
            headline = 'The file-detail checks found no listed clues. These are separate from the trained AI writing estimate above.'
        content += f'<h3 class="section-title">Other file checks</h3><p>{esc(headline)}</p>'
        if text:
            if text.get('characters', 0) == 0:
                content += finding('Text', 'No readable text was found.', 'An empty file has no text to check. A scanned PDF may need text recognition (OCR).')
            else:
                content += finding('Hidden or special characters', f'{hidden:,} found in {text["characters"]:,} characters checked.' if hidden else '0 found. AI-written text can also have 0.', 'These can come from copied text, normal spacing, languages, or emoji. Finding them does not prove AI use, and finding none does not rule it out.')
                content += finding('Words mixing alphabets', f'{mixed:,} found.' if mixed else 'None found.', 'Some letters look alike but belong to different alphabets. Mixed-language writing can be completely normal.')
        if pictures:
            content += finding('Pictures', f'{len(pictures)} picture(s) checked.', 'We read their saved details and made optional pattern views. These views cannot tell you whether a picture was made by AI.')
        if hints:
            content += finding('AI-tool names in saved details', ', '.join(hints), 'These names appear in the file’s stored information. A name can be copied or edited; it does not verify the file’s origin.')
        elif 'metadata' in result or pictures:
            content += finding('AI-tool names in saved details', 'No names from our checklist were found.', 'The file may have no saved history, or its history may have been removed. This is not proof of human authorship.')
        credential = result.get('content_credentials', {})
        if credential:
            state = credential.get('status', '')
            if 'Not checked' in state:
                description = 'Not checked: the optional signature-checking tool is not installed.'
            elif credential.get('error') or credential.get('exit_code', 0) != 0:
                description = 'The optional signature check could not confirm a result. See the technical details.'
            else:
                description = 'The optional signature tool returned a result. Its trust and validation details need review.'
            content += finding('Signed file history', description, 'A signed history may record how a file was created or edited. We do not turn it into an AI or human verdict.')
        if result.get('issues'):
            content += '<div class="limitations"><h3>What could not be fully checked</h3><ul>' + ''.join(f'<li>{esc(i)}</li>' for i in result['issues']) + '</ul></div>'
        content += '<h3 class="section-title">What to do next</h3><p>Treat the model’s result as an estimate. If knowing the source matters, ask for the original file and its creation history. Do not use this report alone to accuse someone of using AI.</p>'
        if hidden or mixed:
            content += '<details class="examples"><summary>See the text findings</summary><p>Locations refer to the text we extracted. They may not match the document’s visible lines. Up to 100 findings of each kind are shown.</p><div class="table-scroll"><table><thead><tr><th>Location</th><th>What was found</th><th>Code or word</th></tr></thead><tbody>'
            for item in text.get('unusual_characters_first_100', []):
                content += f'<tr><td>Line {item["line"]}, position {item["column"]}</td><td>{esc(character_name(item))}</td><td>{esc(item["code"])}</td></tr>'
            for item in text.get('mixed_alphabet_words_first_100', []):
                content += f'<tr><td>Line {item["line"]}, position {item["column"]}</td><td>Letters from {esc(", ".join(item["scripts"]).lower())}</td><td>{esc(item["word"])}</td></tr>'
            content += '</tbody></table></div></details>'
        figures = []
        for pic in pictures:
            for visual in pic.get('visuals', []):
                path = PurePosixPath(visual.get('file', ''))
                if len(path.parts) != 2 or path.parts[0] != 'assets' or path.suffix.lower() != '.png' or '..' in path.parts:
                    continue
                is_fft = 'patterns' in path.name
                title = 'Repeating-pattern view (FFT)' if is_fft else 'Save-again view (ELA)'
                explanation = ('Bright dots and lines show patterns in the picture. Normal pictures can have them too.' if is_fft else 'Bright areas changed more when saved again as a JPEG. Edges and textures often do this naturally.')
                figures.append(f'<figure><h4>{title}</h4><img loading="lazy" src="{esc(path.as_posix())}" alt="{esc(title + " for " + pic.get("source", name))}"><figcaption><strong>{esc(pic.get("source", name))}</strong><br>{explanation}</figcaption></figure>')
        if figures:
            content += f'<details class="image-details"><summary>Show technical images ({len(figures)}) — optional</summary><p>You do not need these images to read the report. Bright areas do not prove AI use or editing.</p><div class="pictures">{"".join(figures)}</div></details>'
        if result.get('warnings'):
            content += '<details><summary>Read the limits of these checks</summary><ul>' + ''.join(f'<li>{esc(w)}</li>' for w in dict.fromkeys(result['warnings'])) + '</ul></details>'
    content += f'<details class="technical"><summary>Show technical data — optional</summary><pre>{esc(json.dumps(result, ensure_ascii=False, indent=2))}</pre></details></article>'
    return content


def render_report(report):
    files = report.get('files', [])
    counts = {kind: sum(file_status(r)[0] == kind for r in files) for kind in ('complete', 'partial', 'failed')}
    overview = f'{len(files)} file(s) · {counts["complete"]} finished · {counts["partial"]} partly checked · {counts["failed"]} could not be checked'
    nav = ''
    if len(files) > 1:
        nav = '<nav aria-label="Files in this report"><h2>Jump to a file</h2><ul>' + ''.join(f'<li><a href="#file-{i}">{esc(Path(r["file"]).name)}</a></li>' for i, r in enumerate(files, 1)) + '</ul></nav>'
    history_note = '<p>This older report has a new layout. Its saved findings have not been scanned again. Run a new check to use the latest scanner.</p>' if report.get('layout_refreshed') else ''
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' file: data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>Your file report — AI File Inspector</title><style>
    :root{color-scheme:light;--ink:#203b33;--muted:#4b625a;--line:#cedbd4;--paper:#f5f6f1;--accent:#175f48}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 'Segoe UI',system-ui,sans-serif}main{max-width:1040px;margin:auto;padding:44px 32px 70px}h1{font-size:clamp(30px,5vw,44px);line-height:1.15;letter-spacing:-.025em;margin:0 0 16px}h2{font-size:23px;line-height:1.3;margin:0;overflow-wrap:anywhere}h3{font-size:16px;margin:0}p{margin:8px 0 16px;max-width:75ch;overflow-wrap:anywhere}.intro{max-width:740px;font-size:18px}.privacy{color:var(--muted);font-size:14px}.overview{font-weight:600;padding:16px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:24px 0}.notice{padding:18px 22px;background:#e7eee8;border-radius:12px;max-width:none}article{margin-top:32px;padding:28px;background:white;border:1px solid var(--line);border-radius:14px;scroll-margin-top:20px}.file-heading{display:flex;gap:16px;justify-content:space-between;align-items:flex-start;flex-wrap:wrap}.file-heading h2{flex:1 1 300px}.status{font-size:13px;font-weight:600;padding:4px 10px;border-radius:6px;background:#edf2ef;color:#315246}.status.partial{background:#fff0d5;color:#745009}.status.failed{background:#fce9e5;color:#8a352b}.message{font-size:18px;margin:18px 0 24px}.section-title{font-size:19px;margin:26px 0 12px}.finding{display:grid;grid-template-columns:210px 1fr;gap:24px;padding:16px 0;border-top:1px solid #e1e7e3}.finding p{margin:0}.finding .explain{color:var(--muted);font-size:14px;margin-top:6px}.limitations{background:#fff5e4;padding:18px;margin:20px 0;border-radius:10px}.limitations ul{margin-bottom:0}details{border-top:1px solid var(--line);padding:0;margin-top:8px}summary{padding:15px 0;cursor:pointer;font-weight:600;min-height:48px;overflow-wrap:anywhere}summary:hover,a:hover{color:#0b432f}summary:focus-visible,a:focus-visible{outline:3px solid #ac6714;outline-offset:4px;border-radius:3px}details[open]{padding-bottom:16px}details[open]>summary{margin-bottom:8px}.pictures{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}figure{margin:0;min-width:0}h4{margin:8px 0}img{width:100%;max-height:330px;object-fit:contain;background:#edf1ed;border-radius:6px}figcaption{font-size:14px;color:var(--muted);overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:560px;overflow:auto;padding:18px;background:#f0f3ef;font-size:13px}a{color:var(--accent);text-underline-offset:4px}nav{margin:28px 0}nav h2{font-size:18px}nav ul{padding-left:22px}nav a{overflow-wrap:anywhere}.table-scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px;text-align:left}td,th{padding:12px 10px;border-bottom:1px solid var(--line);overflow-wrap:anywhere}td:first-child{font-variant-numeric:tabular-nums;min-width:130px}footer{margin-top:32px;color:var(--muted);font-size:14px}::selection{background:#cce5d5;color:#13392b}*{scrollbar-color:#8caaa0 #edf2ef}
    @media(max-width:650px){main{padding:28px 16px 48px}article{padding:20px 16px}.finding{grid-template-columns:1fr;gap:6px}.pictures{grid-template-columns:1fr}.file-heading h2{flex-basis:100%}.notice{padding:16px}.message{font-size:17px}}
    @media print{body{background:white}main{max-width:none;padding:0}article{break-inside:avoid}.image-details:not([open]),.technical:not([open]){display:none}nav{display:none}}
    </style></head><body><main><header><h1>Your file report</h1><p class="intro">An AI writing estimate, with file details you can review.</p><p class="privacy">Checked on your computer. Your original files were not changed.</p></header>''' + f'<p class="overview">{esc(overview)}</p><p class="notice"><strong>A trained detector, not a final verdict</strong><br>The text model estimates whether English writing resembles AI or human examples. It can be wrong, especially with short, edited, or unfamiliar writing. Hidden-character checks are separate. Technical images stay hidden until you open them.</p>{history_note}{nav}' + ''.join(file_section(r, i) for i, r in enumerate(files, 1)) + f'<footer><p>Report created: {esc(report.get("created", "Unknown"))}</p><a href="report.json" download>Save the full technical report (JSON)</a><p>Reports may contain private file details. Share them only with people you intend to.</p></footer></main></body></html>'
