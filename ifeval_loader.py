"""
Fetches real tasks from google/IFEval on HuggingFace and returns them
in the same format as the custom tasks in the runners.

Each IFEval row may have multiple constraints; a compound validator is
built that checks all of them and reports per-constraint results.
"""

import json
import re
import urllib.request

HF_ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=google/IFEval&config=default&split=train"
    "&offset={offset}&limit={limit}"
)


# ── Per-instruction-type validators ───────────────────────────────────────────
# Each fn signature: (response: str, kwargs: dict) -> (passed: bool, detail: str)

def _no_comma(response, kw):
    passed = "," not in response
    return passed, "ok" if passed else "comma found"


def _number_words(response, kw):
    num = kw.get("num_words") or 0
    relation = kw.get("relation") or "at least"
    wc = len(response.split())
    if relation == "at least":
        passed = wc >= num
    elif relation == "at most":
        passed = wc <= num
    else:  # around — within 10 %
        passed = abs(wc - num) <= max(1, int(num * 0.1))
    return passed, f"words={wc} ({relation} {num})"


def _keywords_existence(response, kw):
    keywords = kw.get("keywords") or []
    r_lower = response.lower()
    missing = [k for k in keywords if k.lower() not in r_lower]
    return not missing, ("ok" if not missing else f"missing={missing}")


def _keywords_frequency(response, kw):
    keyword  = kw.get("keyword") or ""
    freq     = kw.get("frequency") or 1
    relation = kw.get("relation") or "at least"
    count    = len(re.findall(re.escape(keyword), response, re.IGNORECASE))
    if relation == "at least":
        passed = count >= freq
    elif relation == "at most":
        passed = count <= freq
    else:
        passed = count == freq
    return passed, f"'{keyword}' ×{count} ({relation} {freq})"


def _forbidden_words(response, kw):
    forbidden = kw.get("forbidden_words") or []
    r_lower = response.lower()
    found = [w for w in forbidden if w.lower() in r_lower]
    return not found, ("ok" if not found else f"found={found}")


def _letter_frequency(response, kw):
    letter   = (kw.get("letter") or "").lower()
    freq     = kw.get("let_frequency") or 0
    relation = kw.get("let_relation") or "at least"
    count    = response.lower().count(letter)
    if relation == "at least":
        passed = count >= freq
    elif relation == "at most":
        passed = count <= freq
    else:
        passed = count == freq
    return passed, f"'{letter}' ×{count} ({relation} {freq})"


def _number_sentences(response, kw):
    num      = kw.get("num_sentences") or 0
    relation = kw.get("relation") or "at least"
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", response.strip()) if s.strip()]
    sc = len(sentences)
    if relation == "at least":
        passed = sc >= num
    elif relation == "at most":
        passed = sc <= num
    else:
        passed = sc == num
    return passed, f"sentences={sc} ({relation} {num})"


def _number_paragraphs(response, kw):
    num      = kw.get("num_paragraphs") or 0
    relation = kw.get("relation") or "at least"
    paragraphs = [p for p in re.split(r"\n\s*\n", response.strip()) if p.strip()]
    pc = len(paragraphs)
    if relation == "at least":
        passed = pc >= num
    elif relation == "at most":
        passed = pc <= num
    else:
        passed = pc == num
    return passed, f"paragraphs={pc} ({relation} {num})"


def _nth_paragraph_first_word(response, kw):
    nth        = kw.get("nth_paragraph") or 1
    first_word = (kw.get("first_word") or "").lower()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", response.strip()) if p.strip()]
    if len(paragraphs) < nth:
        return False, f"only {len(paragraphs)} paragraphs"
    actual = paragraphs[nth - 1].split()[0].lower().strip(".,!?\"'") if paragraphs[nth - 1].split() else ""
    passed = actual == first_word
    return passed, f"para {nth} starts with '{actual}' (need '{first_word}')"


def _number_highlighted(response, kw):
    num   = kw.get("num_highlights") or 0
    found = len(re.findall(r"\*[^*\n]+\*", response))
    passed = found >= num
    return passed, f"highlights={found} (need >={num})"


def _number_bullets(response, kw):
    num   = kw.get("num_bullets") or 0
    found = sum(1 for l in response.splitlines() if re.match(r"^\s*[-*•]", l))
    passed = found >= num
    return passed, f"bullets={found} (need >={num})"


def _json_format(response, kw):
    try:
        json.loads(response.strip())
        return True, "valid JSON"
    except Exception:
        return False, "invalid JSON"


def _title(response, kw):
    passed = bool(re.search(r"<<[^>]+>>", response))
    return passed, "ok" if passed else "no <<title>> found"


def _multiple_sections(response, kw):
    num      = kw.get("num_sections") or 0
    splitter = kw.get("section_spliter") or "Section"
    found    = len(re.findall(rf"(?m)^{re.escape(splitter)}", response))
    passed   = found >= num
    return passed, f"sections={found} (need >={num})"


def _postscript(response, kw):
    marker = kw.get("postscript_marker") or "P.S."
    passed = marker in response
    return passed, "ok" if passed else f"'{marker}' not found"


def _number_placeholders(response, kw):
    num   = kw.get("num_placeholders") or 0
    found = len(re.findall(r"\[[^\]\n]+\]", response))
    passed = found >= num
    return passed, f"placeholders={found} (need >={num})"


def _english_lowercase(response, kw):
    letters = [c for c in response if c.isalpha()]
    passed  = all(c.islower() for c in letters)
    return passed, "ok" if passed else "uppercase letters found"


def _english_capital(response, kw):
    letters = [c for c in response if c.isalpha()]
    passed  = all(c.isupper() for c in letters)
    return passed, "ok" if passed else "lowercase letters found"


def _capital_word_frequency(response, kw):
    freq     = kw.get("capital_frequency") or 0
    relation = kw.get("capital_relation") or "at least"
    cap_words = [w for w in response.split() if w.isupper() and w.isalpha()]
    count = len(cap_words)
    if relation == "at least":
        passed = count >= freq
    elif relation == "at most":
        passed = count <= freq
    else:
        passed = count == freq
    return passed, f"cap_words={count} ({relation} {freq})"


def _repeat_prompt(response, kw):
    prompt = (kw.get("prompt_to_repeat") or "").strip()
    passed = prompt.lower() in response.lower()
    return passed, "ok" if passed else "prompt not repeated"


def _two_responses(response, kw):
    passed = bool(re.search(r"\*{6}", response)) or response.count("****") >= 2
    return passed, "ok" if passed else "response separator not found"


def _quotation(response, kw):
    s = response.strip()
    passed = s.startswith('"') and s.endswith('"')
    return passed, "ok" if passed else "not wrapped in quotes"


def _end_checker(response, kw):
    phrase = kw.get("end_phrase") or ""
    passed = response.strip().endswith(phrase)
    return passed, "ok" if passed else f"ends: '…{response.strip()[-35:]}'"


VALIDATOR_MAP = {
    "punctuation:no_comma":                          _no_comma,
    "length_constraints:number_words":               _number_words,
    "keywords:existence":                            _keywords_existence,
    "keywords:frequency":                            _keywords_frequency,
    "keywords:forbidden_words":                      _forbidden_words,
    "keywords:letter_frequency":                     _letter_frequency,
    "length_constraints:number_sentences":           _number_sentences,
    "length_constraints:number_paragraphs":          _number_paragraphs,
    "length_constraints:nth_paragraph_first_word":   _nth_paragraph_first_word,
    "detectable_format:number_highlighted_sections": _number_highlighted,
    "detectable_format:number_bullet_lists":         _number_bullets,
    "detectable_format:json_format":                 _json_format,
    "detectable_format:title":                       _title,
    "detectable_format:multiple_sections":           _multiple_sections,
    "detectable_content:postscript":                 _postscript,
    "detectable_content:number_placeholders":        _number_placeholders,
    "change_case:english_lowercase":                 _english_lowercase,
    "change_case:english_capital":                   _english_capital,
    "change_case:capital_word_frequency":            _capital_word_frequency,
    "combination:repeat_prompt":                     _repeat_prompt,
    "combination:two_responses":                     _two_responses,
    "startend:quotation":                            _quotation,
    "startend:end_checker":                          _end_checker,
}

# language:response_language requires a language detection library — skipped.
UNSUPPORTED = {"language:response_language"}


def _all_supported(instruction_ids):
    return all(iid in VALIDATOR_MAP for iid in instruction_ids)


def _make_validator(instruction_ids, kwargs_list):
    """Build a compound validator that checks every constraint in a row."""
    pairs = list(zip(instruction_ids, kwargs_list))

    def validator(response):
        details, all_passed = [], True
        for iid, kw in pairs:
            fn = VALIDATOR_MAP.get(iid)
            if fn is None:
                continue
            passed, detail = fn(response, kw)
            if not passed:
                all_passed = False
            tag = iid.split(":")[-1][:12]
            details.append(f"{tag}:{detail}")
        summary = " | ".join(details) if details else "ok"
        return all_passed, summary[:42]

    return validator


# ── Public API ─────────────────────────────────────────────────────────────────

def load_ifeval_tasks(n: int = 6) -> list:
    """
    Fetch n tasks from google/IFEval on HuggingFace.
    Only tasks whose instruction types are all supported are included.
    Returns a list of task dicts compatible with run_no_skills / run_with_skills.
    """
    collected, offset = [], 0

    while len(collected) < n:
        url = HF_ROWS_URL.format(offset=offset, limit=50)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            rows = json.loads(resp.read())["rows"]
        if not rows:
            break

        for row in rows:
            r   = row["row"]
            ids = r["instruction_id_list"]
            kws = r["kwargs"]
            if not _all_supported(ids):
                continue
            short_constraint = ", ".join(i.split(":")[-1] for i in ids)
            collected.append({
                "id":         f"HF{r['key']}",
                "constraint": short_constraint[:42],
                "instruction": r["prompt"],
                "validator":  _make_validator(ids, kws),
            })
            if len(collected) >= n:
                break

        offset += 50

    print(f"  [ifeval_loader] loaded {len(collected)} tasks from google/IFEval")
    return collected
