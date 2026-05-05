"""
IFEval runner WITHOUT skills — calls ollama directly, no tool use.
"""

import json
import re
import urllib.request

OLLAMA_URL = "http://localhost:11434"
MODELS = ["llama3:8b", "qwen2.5:3b"]


# ── Ollama caller ──────────────────────────────────────────────────────────────

def call_ollama(model: str, messages: list) -> str:
    payload = {"model": model, "messages": messages, "stream": False}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["message"]["content"]


# ── Validators ─────────────────────────────────────────────────────────────────

TOOL_CALL_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)


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
            "Do NOT use any bullet points or numbered lists."
        ),
        "validator": validate_keywords_no_bullets,
    },
    {
        "id": "T2",
        "constraint": "Exactly 3 numbered items, each ends with '.'",
        "instruction": (
            "List exactly 3 advantages of remote work. "
            "Format your answer as a numbered list using '1.', '2.', '3.'. "
            "Each item must be a single sentence ending with a period."
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
            "Your response must be at least 50 words long."
        ),
        "validator": validate_min_words,
    },
    {
        "id": "T6",
        "constraint": "Describe gravity without using 'force'",
        "instruction": (
            "Describe the concept of gravity in 2–4 sentences. "
            "You must NOT use the word 'force' anywhere in your response."
        ),
        "validator": validate_forbidden_word,
    },
]


# ── Grid printer ───────────────────────────────────────────────────────────────

def print_grid(results: dict):
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
    print("│" + "IFEval Results  (no skills)".center(total - 2) + "│")
    hline("├", "┬", "┤")
    row("Task", "Constraint", *models)
    hline("├", "┼", "┤")

    scores = {m: 0 for m in models}
    for task in IFEVAL_TASKS:
        tid = task["id"]
        cells = [tid, task["constraint"]]
        for m in models:
            passed, detail = results[m][tid]
            if passed:
                scores[m] += 1
            cells.append(f"{'PASS' if passed else 'FAIL'}  {detail}"[:COL_MODEL])
        row(*cells)

    hline("├", "┼", "┤")
    n = len(IFEVAL_TASKS)
    row("", "Score", *[f"{scores[m]}/{n} ({int(100*scores[m]/n)}%)" for m in models])
    print("└" + "─" * (total - 2) + "┘")
    print()


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_all():
    results = {m: {} for m in MODELS}

    for model in MODELS:
        print(f"\n{'='*60}")
        print(f" Running model: {model}  [no skills]")
        print(f"{'='*60}")
        for task in IFEVAL_TASKS:
            print(f"\n  [{task['id']}] {task['constraint']}")
            messages = [{"role": "user", "content": task["instruction"]}]
            response = call_ollama(model, messages)
            passed, detail = task["validator"](response)
            results[model][task["id"]] = (passed, detail)
            print(f"  → [{'PASS' if passed else 'FAIL'}] {detail}")

    print_grid(results)


if __name__ == "__main__":
    run_all()
