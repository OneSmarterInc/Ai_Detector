AI File Inspector: accuracy reference check
=========================================

What changed
An offline accuracy checker was added. The writing model and its decision rules
have NOT been changed. We have not demonstrated an accuracy improvement yet.
The checker lets us measure future changes instead of guessing.

Result on 3 November 2026
80 examples: 40 human answers and 40 ChatGPT answers.
64 correct, 9 wrong, 7 Not sure. No skipped examples or runtime errors.
4 human answers were wrongly called AI. 5 AI answers were called human.

Subject                  Correct   Wrong   Not sure   Total
Finance                    11        2        3        16
Medicine                   16        0        0        16
General questions          16        0        0        16
Everyday explanations      13        2        1        16
Computer/AI explanations    8        5        3        16

These are SMALL reference samples, NOT a claim of real-world accuracy.
The model may have seen HC3 material during training. The sample is not random,
has only 8 human/AI pairs per subject, and does not cover modern model families,
stories, essays, edited AI writing or mixed human/AI documents adequately.
Do not use the perfect scores in two subjects as proof of reliability.

Source and selection
https://huggingface.co/datasets/Hello-SimpleAI/HC3
Public train split, finance, medicine, open_qa, reddit_eli5, wiki_csai configs.
Retrieved first 30 rows of each config via the Hugging Face dataset viewer.
Used the first 8 pairs where the first human answer and first ChatGPT answer
each had at least 100 regex word tokens. The installed detector separately
applied its own word-count and language checks. No thresholds were tuned.
Source texts are not included in this report. Row IDs and file/model hashes
are recorded in reference-results.json. Downloaded inputs remain in the
workspace's work/accuracy-study folder. HC3 is listed as CC-BY-SA-4.0.

Best next improvements for mixed writing
1. Collect known-origin examples across essays, stories, reports, emails,
   technical writing and everyday explanations, including current AI models.
2. Include AI text edited by people and real human writing with simple English.
3. Keep development examples separate from final test examples. Keep texts
   from the same source/prompt in one set to avoid misleading results.
4. Compare newer detectors with this model. Only combine models if a separate
   test shows fewer mistakes without an unacceptable rise in Not sure results.
5. Tune decision cutoffs on development data, then freeze them and test on
   fresh data. Track human false alarms, missed AI, uncertainty and coverage.
6. Consider training/fine-tuning on diverse labelled data if comparison and
   calibration are insufficient. This needs more data and compute.

Keeping Not sure is necessary when evidence is weak. Removing it only makes
the answer more definite; it does not make detection more accurate.
Hidden characters do not prove who wrote a document.

How to use the checker
Create a UTF-8 JSONL file, one object per line:
{"id":"essay-001","label":"human","domain":"essay","text":"Paste full known-origin text here."}
Use label human or ai only. Do not guess labels from another detector.
Mixed-origin documents need a separate evaluation design; do not force them
into either label. At least 100 English words are needed by this model.
Duplicate text and IDs are rejected to prevent inflated counts.

Run with the same Python installation used by Start Inspector.bat:
python -B check_accuracy.py examples.jsonl --app <project-folder> --output results.json

The checker runs locally. Reports save IDs and scores, not example text.
Uncertain, skipped and failed checks are counted separately, never as correct.
Results include correctness among clear answers AND how often it gave a clear
answer. Never quote the former alone as overall accuracy.

Validation
4 accuracy-checker tests passed (counting, no clear answers, duplicate rejection,
invalid labels). An end-to-end run scored all 80 examples using the installed
model. Existing application files were unchanged.

Research supporting broader evaluation:
https://aclanthology.org/2024.acl-long.674/
