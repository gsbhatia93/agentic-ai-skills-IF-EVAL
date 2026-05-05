"""
IFEval runner WITH skills — structured tool calling (Anthropic-style).

Skills are defined as JSON schemas and passed to ollama's native tool-calling
API. The model returns structured tool_calls; the agent loop executes each
skill and feeds results back as role:tool messages.

Models that don't support tool calling are skipped gracefully.
skills.md is retained as human-readable documentation only.
"""

import json
import re
import urllib.request

OLLAMA_URL = "http://localhost:11434"


def get_models() -> list:
    req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return [m["name"] for m in json.loads(resp.read())["models"]]


# ── Skills ─────────────────────────────────────────────────────────────────────

def count_words(text: str) -> dict:
    words = text.split()
    return {"word_count": len(words), "char_count": len(text)}


def check_keywords(text: str, keywords: list) -> dict:
    text_lower = text.lower()
    found = [k for k in keywords if k.lower() in text_lower]
    missing = [k for k in keywords if k.lower() not in text_lower]
    return {"found": found, "missing": missing, "all_present": len(missing) == 0}


def check_no_comma(text: str) -> dict:
    has_comma = "," in text
    return {"has_comma": has_comma, "passed": not has_comma}


def count_highlighted_sections(text: str) -> dict:
    count = len(re.findall(r"\*[^*\n]+\*", text))
    return {"count": count}


def count_placeholders(text: str) -> dict:
    count = len(re.findall(r"\[[^\]\n]+\]", text))
    return {"count": count}


def check_title_format(text: str) -> dict:
    has_title = bool(re.search(r"<<[^>]+>>", text))
    return {"has_title": has_title}


def check_case(text: str, case: str) -> dict:
    letters = [c for c in text if c.isalpha()]
    if case == "lower":
        passed = all(c.islower() for c in letters)
        detail = "ok" if passed else "uppercase letters found"
    elif case == "upper":
        passed = all(c.isupper() for c in letters)
        detail = "ok" if passed else "lowercase letters found"
    else:
        passed, detail = False, f"unknown case: {case}"
    return {"passed": passed, "detail": detail}


def count_bullets(text: str) -> dict:
    count = sum(1 for l in text.splitlines() if re.match(r"^\s*[-*•]", l))
    return {"count": count}


def count_sections(text: str, splitter: str) -> dict:
    count = len(re.findall(rf"(?m)^{re.escape(splitter)}", text))
    return {"count": count}


def count_capital_words(text: str) -> dict:
    count = len([w for w in text.split() if w.isupper() and w.isalpha()])
    return {"count": count}


def check_json_format(text: str) -> dict:
    try:
        json.loads(text.strip())
        return {"passed": True, "detail": "valid JSON"}
    except Exception as e:
        return {"passed": False, "detail": f"invalid JSON: {str(e)[:40]}"}


def count_paragraphs(text: str) -> dict:
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return {"count": len(paragraphs)}


def check_two_responses(text: str) -> dict:
    passed = "******" in text
    return {"passed": passed, "detail": "ok" if passed else "****** separator not found"}


def count_letter_frequency(text: str, letter: str) -> dict:
    count = text.lower().count(letter.lower())
    return {"count": count}


def check_ends_with(text: str, phrase: str) -> dict:
    passed = text.strip().endswith(phrase)
    detail = "ok" if passed else f"ends with: '...{text.strip()[-40:]}'"
    return {"passed": passed, "detail": detail}


def check_starts_with_prompt(text: str, prompt: str) -> dict:
    passed = text.strip().startswith(prompt.strip())
    detail = "ok" if passed else f"starts with: '{text.strip()[:40]}'"
    return {"passed": passed, "detail": detail}


def check_quotation(text: str) -> dict:
    s = text.strip()
    passed = s.startswith('"') and s.endswith('"')
    detail = "ok" if passed else "response not wrapped in double quotes"
    return {"passed": passed, "detail": detail}


SKILL_MAP = {
    "count_words":                count_words,
    "check_keywords":             check_keywords,
    "check_no_comma":             check_no_comma,
    "count_highlighted_sections": count_highlighted_sections,
    "count_placeholders":         count_placeholders,
    "check_title_format":         check_title_format,
    "check_case":                 check_case,
    "count_bullets":              count_bullets,
    "count_sections":             count_sections,
    "count_capital_words":        count_capital_words,
    "check_starts_with_prompt":   check_starts_with_prompt,
    "check_quotation":            check_quotation,
    "check_json_format":          check_json_format,
    "count_paragraphs":           count_paragraphs,
    "check_two_responses":        check_two_responses,
    "count_letter_frequency":     count_letter_frequency,
    "check_ends_with":            check_ends_with,
}

# ── Tool definitions (JSON schema) ─────────────────────────────────────────────
# Authoritative skill definitions — skills.md is human-readable docs of these.

def _tool(name, description, properties, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }

_str  = {"type": "string"}
_int  = {"type": "integer"}
_list = {"type": "array", "items": {"type": "string"}}

SKILL_DEFINITIONS = [
    _tool("count_words",               "Count words and characters in text.",                                      {"text": _str}, ["text"]),
    _tool("check_keywords",            "Check which keywords are present or missing in text.",                     {"text": _str, "keywords": _list}, ["text", "keywords"]),
    _tool("check_no_comma",            "Check that text contains no commas.",                                      {"text": _str}, ["text"]),
    _tool("count_highlighted_sections","Count *highlighted* sections (markdown italics) in text.",                 {"text": _str}, ["text"]),
    _tool("count_placeholders",        "Count [placeholder] patterns in text.",                                    {"text": _str}, ["text"]),
    _tool("check_title_format",        "Check that text contains a <<Title>> marker.",                             {"text": _str}, ["text"]),
    _tool("check_case",                "Check letter casing. case must be 'lower' or 'upper'.",                   {"text": _str, "case": _str}, ["text", "case"]),
    _tool("count_bullets",             "Count bullet list items (lines starting with -, *, or •).",               {"text": _str}, ["text"]),
    _tool("count_sections",            "Count sections that begin with a given splitter word.",                    {"text": _str, "splitter": _str}, ["text", "splitter"]),
    _tool("count_capital_words",       "Count words that are entirely UPPERCASE.",                                 {"text": _str}, ["text"]),
    _tool("check_starts_with_prompt",  "Check that text begins by repeating the original prompt.",                 {"text": _str, "prompt": _str}, ["text", "prompt"]),
    _tool("check_quotation",           "Check that text is wrapped in double quotation marks.",                    {"text": _str}, ["text"]),
    _tool("check_json_format",         "Check that text is valid JSON.",                                           {"text": _str}, ["text"]),
    _tool("count_paragraphs",          "Count paragraphs (blocks separated by blank lines).",                     {"text": _str}, ["text"]),
    _tool("check_two_responses",       "Check that text contains two responses divided by ****** .",              {"text": _str}, ["text"]),
    _tool("count_letter_frequency",    "Count occurrences of a specific letter (case-insensitive).",              {"text": _str, "letter": _str}, ["text", "letter"]),
    _tool("check_ends_with",           "Check that text ends with an exact phrase.",                              {"text": _str, "phrase": _str}, ["text", "phrase"]),
]


# ── Ollama caller ──────────────────────────────────────────────────────────────

DEBUG = True  # set False to silence debug output


def _dbg(msg: str):
    if DEBUG:
        print(f"    [debug] {msg}")


def _call_ollama(model: str, messages: list, tools: list) -> dict:
    """Returns the raw message dict from ollama (may contain tool_calls)."""
    payload = {"model": model, "messages": messages, "tools": tools, "stream": False}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["message"]


def _execute(fn_name: str, fn_args: dict) -> str:
    _dbg(f"skill call → {fn_name}({fn_args})")
    fn = SKILL_MAP.get(fn_name)
    if fn is None:
        _dbg(f"UNKNOWN skill '{fn_name}' — available: {list(SKILL_MAP.keys())}")
        return json.dumps({"error": f"unknown skill: {fn_name}"})
    try:
        result = fn(**fn_args)
        _dbg(f"result    → {result}")
        return json.dumps(result)
    except Exception as exc:
        _dbg(f"ERROR     → {exc}")
        return json.dumps({"error": str(exc)})


def supports_tools(model: str) -> bool:
    """Quick probe — returns True if model accepts tools without error."""
    try:
        probe = [{"role": "user", "content": "hi"}]
        _call_ollama(model, probe, SKILL_DEFINITIONS[:1])
        return True
    except Exception:
        return False


def run_agent(model: str, user_prompt: str, max_rounds: int = 3) -> str:
    messages = [{"role": "user", "content": user_prompt}]

    for round_num in range(max_rounds):
        _dbg(f"round {round_num + 1}/{max_rounds} — calling {model}")
        msg = _call_ollama(model, messages, SKILL_DEFINITIONS)

        tool_calls = msg.get("tool_calls") or []
        _dbg(f"tool_calls received: {len(tool_calls)}")

        if not tool_calls:
            _dbg("no tool calls — final answer")
            return (msg.get("content") or "").strip()

        # Append assistant turn then execute each tool call
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls})
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            fn_args = tc["function"].get("arguments", {})
            if isinstance(fn_args, str):
                fn_args = json.loads(fn_args)
            messages.append({
                "role":    "tool",
                "content": _execute(fn_name, fn_args),
            })

    _dbg("max rounds reached — returning last content")
    return (msg.get("content") or "").strip()


# ── Validators ─────────────────────────────────────────────────────────────────

def validate_keywords_no_bullets(response: str) -> tuple:
    required = ["carbon", "renewable", "future"]
    r_lower = response.lower()
    missing = [k for k in required if k not in r_lower]
    has_bullets = any(
        line.strip().startswith(("-", "*", "•")) for line in response.splitlines()
    )
    passed = not missing and not has_bullets
    detail = f"missing={missing}" if missing else ("bullets found" if has_bullets else "ok")
    return passed, detail


def validate_numbered_list_3(response: str) -> tuple:
    lines = [l.strip() for l in response.splitlines() if l.strip()]
    numbered = [l for l in lines if len(l) > 2 and l[:2] in ("1.", "2.", "3.")]
    correct_count = len(numbered) == 3
    all_end_period = bool(numbered) and all(l.rstrip().endswith(".") for l in numbered)
    passed = correct_count and all_end_period
    detail = f"items={len(numbered)}, end_period={all_end_period}"
    return passed, detail


def validate_two_sentences(response: str) -> tuple:
    clean = TOOL_CALL_RE.sub("", response).strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
    passed = len(sentences) == 2
    detail = f"sentences={len(sentences)}"
    return passed, detail


def validate_ends_with_phrase(response: str) -> tuple:
    phrase = "This is the essence of neural networks."
    passed = response.rstrip().endswith(phrase)
    detail = "ok" if passed else f"ends with: '{response.rstrip()[-40:]}'"
    return passed, detail


def validate_min_words(response: str) -> tuple:
    wc = len(response.split())
    passed = wc >= 50
    detail = f"words={wc} (need ≥50)"
    return passed, detail


def validate_forbidden_word(response: str) -> tuple:
    forbidden = "force"
    found = forbidden.lower() in response.lower()
    passed = not found
    detail = "ok" if passed else f"'{forbidden}' found in response"
    return passed, detail


# ── IFEval tasks ───────────────────────────────────────────────────────────────

IFEVAL_TASKS = [
    {
        "id": "T1",
        "constraint": "Keywords (carbon,renewable,future) + no bullets",
        "instruction": (
            "Write a short paragraph (3–5 sentences) about climate change. "
            "Your response MUST include the words 'carbon', 'renewable', and 'future' at least once each. "
            "Do NOT use any bullet points or numbered lists in your final answer. "
            "You may use the check_keywords skill on your draft before finalising."
        ),
        "validator": validate_keywords_no_bullets,
    },
    {
        "id": "T2",
        "constraint": "Exactly 3 numbered items, each ends with '.'",
        "instruction": (
            "List exactly 3 advantages of remote work. "
            "Format your answer as a numbered list using '1.', '2.', '3.'. "
            "Each item must be a single sentence ending with a period. "
            "You may use the count_words skill to check your response."
        ),
        "validator": validate_numbered_list_3,
    },
    {
        "id": "T3",
        "constraint": "Exactly 2 sentences about the moon",
        "instruction": (
            "Write exactly 2 sentences about the moon. "
            "Your response must be exactly 2 sentences — no more, no less. "
            "Do not use bullet points or lists."
        ),
        "validator": validate_two_sentences,
    },
    {
        "id": "T4",
        "constraint": "Must end with exact phrase",
        "instruction": (
            "Explain what a neural network is in 3–5 sentences. "
            "Your response MUST end with this exact phrase: "
            "'This is the essence of neural networks.'"
        ),
        "validator": validate_ends_with_phrase,
    },
    {
        "id": "T5",
        "constraint": "At least 50 words about space exploration",
        "instruction": (
            "Write a paragraph about space exploration. "
            "Your response must be at least 50 words long. "
            "You may use the count_words skill to verify your word count before finalising."
        ),
        "validator": validate_min_words,
    },
    {
        "id": "T6",
        "constraint": "Describe gravity without using 'force'",
        "instruction": (
            "Describe the concept of gravity in 2–4 sentences. "
            "You must NOT use the word 'force' anywhere in your response. "
            "You may use the check_keywords skill to verify the word is absent."
        ),
        "validator": validate_forbidden_word,
    },
]


# ── Grid printer ───────────────────────────────────────────────────────────────

def print_grid(results: dict, tasks: list = None):
    COL_TASK   = 4
    COL_CONSTR = 42
    COL_MODEL  = 14

    models = list(results.keys())

    def pad(s, w):
        return str(s)[:w].ljust(w)

    sep_widths = [COL_TASK, COL_CONSTR] + [COL_MODEL] * len(models)
    total = sum(sep_widths) + len(sep_widths) * 3 + 1

    def hline(left="├", mid="┼", right="┤", fill="─"):
        parts = [fill * (w + 2) for w in sep_widths]
        print(left + mid.join(parts) + right)

    def row(*cells):
        parts = [f" {pad(c, w)} " for c, w in zip(cells, sep_widths)]
        print("│" + "│".join(parts) + "│")

    print()
    print("┌" + "─" * (total - 2) + "┐")
    print("│" + "IFEval Results  (with skills)".center(total - 2) + "│")
    hline("├", "┬", "┤")
    row("Task", "Constraint", *models)
    hline("├", "┼", "┤")

    task_list = tasks or IFEVAL_TASKS
    scores = {m: 0 for m in models}
    for task in task_list:
        tid = task["id"]
        cells = [tid, task["constraint"]]
        for m in models:
            passed, detail = results[m][tid]
            if passed:
                scores[m] += 1
            cells.append(f"{'PASS' if passed else 'FAIL'}  {detail}"[:COL_MODEL])
        row(*cells)

    hline("├", "┼", "┤")
    n = len(task_list)
    row("", "Score", *[f"{scores[m]}/{n} ({int(100*scores[m]/n)}%)" for m in models])
    print("└" + "─" * (total - 2) + "┘")
    print()


# ── Evaluate / Runner ──────────────────────────────────────────────────────────

def evaluate(model: str, tasks: list = None) -> dict:
    """Run all tasks for one model. Returns {task_id: (passed, detail)}."""
    tasks = tasks or IFEVAL_TASKS

    if not supports_tools(model):
        print(f"    [SKIP] {model} does not support tool calling")
        return {t["id"]: (False, "tools unsupported") for t in tasks}

    results = {}
    for task in tasks:
        try:
            response = run_agent(model, task["instruction"])
            passed, detail = task["validator"](response)
        except Exception as e:
            passed, detail = False, f"error: {str(e)[:30]}"
        results[task["id"]] = (passed, detail)
        print(f"    [{task['id']}] [{'PASS' if passed else 'FAIL'}] {detail}")
    return results


def run_all(tasks: list = None):
    tasks = tasks or IFEVAL_TASKS
    models = get_models()
    print(f"  Models found: {models}")
    results = {}

    for model in models:
        print(f"\n{'='*60}")
        print(f" Running model: {model}  [with skills]")
        print(f"{'='*60}")
        results[model] = evaluate(model, tasks)

    print_grid(results, tasks)


if __name__ == "__main__":
    run_all()
