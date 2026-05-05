You have access to the following skills you may call before writing your final answer.
To call a skill, output a JSON block with the marker exactly like this:

<tool_call>{"name": "skill_name", "args": {...}}</tool_call>

After seeing the skill result (provided as <tool_result>...</tool_result>), revise if needed
and write your final answer. Do NOT include any <tool_call> markers in your final answer.

Available skills:

1. count_words(text: str)  →  {"word_count": int, "char_count": int}
   Use to verify your draft meets a word-count requirement.

2. check_keywords(text: str, keywords: [str])  →  {"found": [...], "missing": [...], "all_present": bool}
   Use to verify required keywords appear in your draft.

3. check_no_comma(text: str)  →  {"has_comma": bool, "passed": bool}
   Use to verify your response contains no commas.

4. count_highlighted_sections(text: str)  →  {"count": int}
   Counts sections marked with markdown italics like *highlighted text*.
   Use to verify you have the required number of highlighted sections.

5. count_placeholders(text: str)  →  {"count": int}
   Counts placeholders in the format [placeholder_name].
   Use to verify you have included the required number of placeholders.

6. check_title_format(text: str)  →  {"has_title": bool}
   Checks that your response contains a title in double angular brackets like <<Title Here>>.

7. check_case(text: str, case: str)  →  {"passed": bool, "detail": str}
   Checks letter casing. case must be "lower" (all lowercase) or "upper" (all uppercase).

8. count_bullets(text: str)  →  {"count": int}
   Counts bullet list items (lines starting with -, *, or •).
   Use to verify you have the required number of bullet points.

9. count_sections(text: str, splitter: str)  →  {"count": int}
   Counts the number of sections that begin with the given splitter word (e.g. "Section").
   Use to verify you have the required number of sections.

10. count_capital_words(text: str)  →  {"count": int}
    Counts words that are entirely in UPPERCASE (e.g. "NASA", "IMPORTANT").
    Use to verify your response has the required number of capitalized words.

11. check_starts_with_prompt(text: str, prompt: str)  →  {"passed": bool, "detail": str}
    Checks that your response begins by repeating the original prompt exactly.
    Use when the task requires you to first repeat the prompt before answering.

12. check_quotation(text: str)  →  {"passed": bool, "detail": str}
    Checks that your entire response is wrapped in double quotation marks.
    Use when the task requires the full response to start with " and end with ".

13. check_json_format(text: str)  →  {"passed": bool, "detail": str}
    Checks that your entire response is valid JSON.
    Use when the task requires the output to be wrapped in JSON format.

14. count_paragraphs(text: str)  →  {"count": int}
    Counts the number of paragraphs (blocks of text separated by blank lines).
    Use to verify your response has the required number of paragraphs.

15. check_two_responses(text: str)  →  {"passed": bool, "detail": str}
    Checks that your response contains two separate answers divided by exactly 6 asterisks (******).
    Use when the task requires two distinct responses.

16. count_letter_frequency(text: str, letter: str)  →  {"count": int}
    Counts how many times a specific letter appears in the response (case-insensitive).
    Use to verify the required letter frequency constraint.

17. check_ends_with(text: str, phrase: str)  →  {"passed": bool, "detail": str}
    Checks that your response ends with an exact phrase.
    Use when the task requires a specific ending phrase.
