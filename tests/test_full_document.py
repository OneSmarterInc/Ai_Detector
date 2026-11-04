import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from xml.etree import ElementTree

from ai_file_inspector.core import detector, scanner
from ai_file_inspector.core.percentages import percentage_breakdown
from docx import Document


class RecordingTokenizer:
    def __init__(self):
        self.texts = []
        self.next_id = 100

    def encode(self, text, **kwargs):
        self.texts.append(text)
        offsets = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
        ids = list(range(self.next_id, self.next_id + len(offsets)))
        self.next_id += len(offsets)
        return SimpleNamespace(ids=ids, offsets=offsets)


class RecordingEngine:
    def __init__(self, fail_at=None):
        self.seen = []
        self.calls = 0
        self.fail_at = fail_at

    def get_inputs(self):
        return [SimpleNamespace(name=n) for n in ("input_ids", "attention_mask")]

    def run(self, outputs, inputs):
        self.calls += 1
        if self.calls == self.fail_at:
            raise RuntimeError("Simulated inference failure")
        self.seen.extend(inputs["input_ids"][0, 1:-1].tolist())
        return [[[3.0]]]


class FullDocumentTests(unittest.TestCase):
    def test_every_token_after_old_character_and_section_limits_is_scored(self):
        text = (
            "This paragraph contains useful English writing for the complete document. "
            * 4000
        ) + " FINAL_SENTINEL"
        self.assertGreater(len(text), 200000)
        engine, tokenizer = RecordingEngine(), RecordingTokenizer()
        with (
            patch.object(detector, "language", return_value=("en", 1)),
            patch.object(detector, "get_engine", return_value=(engine, tokenizer)),
        ):
            result = detector.analyze(text)
        self.assertEqual(result["status"], "estimated", result)
        self.assertEqual("".join(tokenizer.texts), detector.clean_prose(text))
        self.assertTrue(
            all(len(t) <= detector.TOKENIZATION_BLOCK_CHARS for t in tokenizer.texts)
        )
        self.assertEqual(engine.seen, list(range(100, tokenizer.next_id)))
        self.assertGreater(engine.calls, 12)
        self.assertEqual(result["characters_considered"], len(text))
        self.assertEqual(
            result["passages"][-1]["end_character"], len(detector.clean_prose(text))
        )
        self.assertEqual(result["tokens_checked"], len(engine.seen))
        self.assertFalse(percentage_breakdown(result)["sampled"])

    def test_midway_failure_never_produces_a_final_percentage(self):
        text = "This is ordinary English prose in a long document. " * 2000
        engine, tokenizer = RecordingEngine(fail_at=15), RecordingTokenizer()
        with (
            patch.object(detector, "language", return_value=("en", 1)),
            patch.object(detector, "get_engine", return_value=(engine, tokenizer)),
        ):
            result = detector.analyze(text)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["coverage"], "incomplete")
        self.assertEqual(result["passages_checked"], 14)
        self.assertNotIn("ai_pattern_score", result)
        self.assertIsNone(percentage_breakdown(result))

    def test_block_boundaries_never_omit_characters(self):
        for text in ["", "word " * 30000, "a" * 50001]:
            ranges = list(detector.text_blocks(text))
            self.assertEqual("".join(text[a:b] for a, b in ranges), text)
            self.assertTrue(
                all(
                    a < b and b - a <= detector.TOKENIZATION_BLOCK_CHARS
                    for a, b in ranges
                )
            )

    def test_word_text_boxes_nested_tables_and_tracked_text(self):
        xml = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
        <w:p><w:r><w:t>BODY</w:t></w:r><w:txbxContent><w:p><w:r><w:t>BOX</w:t></w:r></w:p></w:txbxContent></w:p>
        <w:tbl><w:tr><w:tc><w:tbl><w:tr><w:tc><w:p><w:r><w:t>NESTED</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:tc></w:tr></w:tbl>
        <w:del><w:p><w:r><w:t>DELETED</w:t></w:r></w:p></w:del><w:ins><w:p><w:r><w:t>INSERTED</w:t></w:r></w:p></w:ins>
        </w:body></w:document>"""
        text = scanner.word_xml_text(ElementTree.fromstring(xml))
        for expected in ["BODY", "BOX", "NESTED", "INSERTED"]:
            self.assertEqual(text.count(expected), 1)
        self.assertNotIn("DELETED", text)

    def test_docx_notes_and_even_headers_reach_the_detector(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "test.docx"
            assets = root / "assets"
            assets.mkdir()
            doc = Document()
            doc.add_paragraph("BODY")
            doc.sections[0].even_page_header.paragraphs[0].text = "EVEN_HEADER"
            doc.save(path)
            with zipfile.ZipFile(path, "a") as archive:
                for name, word in [("footnotes", "FOOTNOTE"), ("endnotes", "ENDNOTE")]:
                    archive.writestr(
                        f"word/{name}.xml",
                        f'<w:notes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>{word}</w:t></w:r></w:p></w:notes>',
                    )
            with patch.object(
                detector, "analyze", return_value={"status": "not_checked"}
            ) as analyze:
                scanner.inspect_file(path, assets, [0])
            text = analyze.call_args.args[0]
            for word in ["BODY", "EVEN_HEADER", "FOOTNOTE", "ENDNOTE"]:
                self.assertEqual(text.count(word), 1)
