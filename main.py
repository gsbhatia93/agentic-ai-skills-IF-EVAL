"""
IFEval (Instruction Following Evaluation) runner with ollama + skills (ReAct-style tool use).

Skills (count_words, check_keywords) are injected into the system prompt.
The model can invoke them via a JSON tool-call marker; the agent loop
executes each call and feeds results back before the model gives its final answer.

Two IFEval tasks are included, each with a verifiable constraint validator.
"""

import json
import re
import urllib.request

OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3:8b"

# ── Skills ─────────────────────────────────────────────────────────────────────

def count_words(text: str) -> dict:
    words = text.split()
    return {"word_count": len(words), "char_count": len(text)}


def check_keywords(text: str, keywords: list) -> dict:
    text_lower = text.lower()
    found = [k for k in keywords if k.lower() in text_lower]
    missing = [k for k in keywords if k.lower() not in text_lower]
    return {"found": found, "missing": missing, "all_present": len(missing) == 0}


SKILL_MAP = {
    "count_words": count_words,
    "check_keywords": check_keywords,
}

SKILL_DESCRIPTIONS = """
You have access to two skills you may call before writing your final answer.
To call a skill, output a JSON block with the marker exactly like this:

<tool_call>{"name": "count_words", "args": {"text": "some text"}}</tool_call>

Available skills:
1. count_words(text: str)  →  {"word_count": int, "char_count": int}
   Use this to verify that your draft meets a word-count requirement.

2. check_keywords(text: str, keywords: [str])  →  {"found": [...], "missing": [...], "all_present": bool}
   Use this to verify that required keywords appear in your draft.

After seeing the skill result (provided as <tool_result>...</tool_result>), revise if needed
and write your final answer. Do not include any <tool_call> markers in your final answer.
"""


# ── Ollama caller ──────────────────────────────────────────────────────────────

def call_ollama(messages: list) -> str:
    payload = {"model": MODEL, "messages": messages, "stream": False}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["message"]["content"]


def execute_tool_call(raw: str) -> str:
    """Parse and run a single <tool_call>...</tool_call> block."""
    try:
        call = json.loads(raw)
        fn_name = call["name"]
        fn_args = call.get("args", {})
        fn = SKILL_MAP.get(fn_name)
        if fn is None:
            return json.dumps({"error": f"unknown skill: {fn_name}"})
        result = fn(**fn_args)
        print(f"  [skill] {fn_name}({fn_args}) → {result}")
        return json.dumps(result)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ── Agent loop ─────────────────────────────────────────────────────────────────

TOOL_CALL_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)

def run_agent(user_prompt: str, max_rounds: int = 5) -> str:
    """
    ReAct-style agent loop:
    1. Model responds with optional <tool_call> blocks.
    2. We execute each skill and inject <tool_result> back.
    3. Repeat until the model produces a response with no tool calls.
    """
    system_msg = {"role": "system", "content": SKILL_DESCRIPTIONS.strip()}
    messages = [system_msg, {"role": "user", "content": user_prompt}]

    for _ in range(max_rounds):
        reply = call_ollama(messages)

        tool_calls = TOOL_CALL_RE.findall(reply)
        if not tool_calls:
            # No tool invocations — this is the final answer
            return reply.strip()

        # Build assistant turn with results injected
        result_blocks = "\n".join(
            f"<tool_result>{execute_tool_call(tc)}</tool_result>"
            for tc in tool_calls
        )
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content": result_blocks})

    return reply.strip()


# ── IFEval validators ──────────────────────────────────────────────────────────

def validate_task1(response: str) -> dict:
    """Keywords: carbon, renewable, future — no bullet points."""
    required = ["carbon", "renewable", "future"]
    r_lower = response.lower()
    missing = [k for k in required if k not in r_lower]
    has_bullets = any(
        line.strip().startswith(("-", "*", "•")) for line in response.splitlines()
    )
    return {
        "passed": not missing and not has_bullets,
        "missing_keywords": missing,
        "has_bullet_points": has_bullets,
    }


def validate_task2(response: str) -> dict:
    """Exactly 3 numbered items (1. 2. 3.), each ending with a period."""
    lines = [l.strip() for l in response.splitlines() if l.strip()]
    numbered = [l for l in lines if len(l) > 2 and l[:2] in ("1.", "2.", "3.")]
    correct_count = len(numbered) == 3
    all_end_period = bool(numbered) and all(l.rstrip().endswith(".") for l in numbered)
    return {
        "passed": correct_count and all_end_period,
        "numbered_items_found": len(numbered),
        "all_end_with_period": all_end_period,
    }


# ── IFEval task definitions ────────────────────────────────────────────────────

IFEVAL_TASKS = [
    {
        "id": "ifeval_001",
        "description": "Keywords: carbon, renewable, future — no bullet points",
        "instruction": (
            "Write a short paragraph (3–5 sentences) about climate change. "
            "Your response MUST include the words 'carbon', 'renewable', and 'future' at least once each. "
            "Do NOT use any bullet points or numbered lists in your final answer. "
            "You may use the check_keywords skill on your draft before finalising."
        ),
        "validator": validate_task1,
    },
    {
        "id": "ifeval_002",
        "description": "Exactly 3 numbered items, each a single sentence ending with '.'",
        "instruction": (
            "List exactly 3 advantages of remote work. "
            "Format your answer as a numbered list using '1.', '2.', '3.'. "
            "Each item must be a single sentence ending with a period. "
            "You may use the count_words skill to check your response length."
        ),
        "validator": validate_task2,
    },
]


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_ifeval_tasks():
    print(f"Model : {MODEL}")
    print(f"Skills: {list(SKILL_MAP.keys())}")
    print("=" * 60)

    for task in IFEVAL_TASKS:
        print(f"\nTask  : {task['id']}  —  {task['description']}")
        print(f"Prompt: {task['instruction']}\n")

        response = run_agent(task["instruction"])

        print(f"Response:\n{response}\n")

        result = task["validator"](response)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"Validation [{status}]: {result}")
        print("-" * 60)


if __name__ == "__main__":
    run_ifeval_tasks()
