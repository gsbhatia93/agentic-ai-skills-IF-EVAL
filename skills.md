You have access to two skills you may call before writing your final answer.
To call a skill, output a JSON block with the marker exactly like this:

<tool_call>{"name": "count_words", "args": {"text": "some text"}}</tool_call>

Available skills:

1. count_words(text: str)  →  {"word_count": int, "char_count": int}
   Use this to verify your draft meets a word-count requirement.

2. check_keywords(text: str, keywords: [str])  →  {"found": [...], "missing": [...], "all_present": bool}
   Use this to verify required keywords appear in your draft.

After seeing the skill result (provided as <tool_result>...</tool_result>), revise if needed
and write your final answer. Do NOT include any <tool_call> markers in your final answer.
