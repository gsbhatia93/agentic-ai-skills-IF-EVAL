# IFEval Skills — Tool Reference

Skills are passed to the model as structured tools via the API (Anthropic-style tool use).
The model receives these as callable tools and returns `tool_use` blocks; the runner
executes each tool and feeds results back as `tool_result` messages before the model
produces its final answer.

---

## Available Tools

### `count_words`
Count the number of words and characters in a text.

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |

**Returns:** `{"word_count": int, "char_count": int}`

---

### `check_keywords`
Check which keywords are present or missing in a text.

| Parameter  | Type            | Required |
|------------|-----------------|----------|
| `text`     | string          | yes      |
| `keywords` | array of string | yes      |

**Returns:** `{"found": [...], "missing": [...], "all_present": bool}`

---

### `check_no_comma`
Check that a text contains no commas.

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |

**Returns:** `{"has_comma": bool, "passed": bool}`

---

### `count_highlighted_sections`
Count sections marked with markdown italics (`*highlighted text*`).

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |

**Returns:** `{"count": int}`

---

### `count_placeholders`
Count placeholders in the format `[placeholder_name]`.

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |

**Returns:** `{"count": int}`

---

### `check_title_format`
Check that a text contains a title in double angular brackets (`<<Title Here>>`).

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |

**Returns:** `{"has_title": bool}`

---

### `check_case`
Check letter casing of a text.

| Parameter | Type   | Required | Notes                        |
|-----------|--------|----------|------------------------------|
| `text`    | string | yes      |                              |
| `case`    | string | yes      | `"lower"` or `"upper"` only  |

**Returns:** `{"passed": bool, "detail": str}`

---

### `count_bullets`
Count bullet list items (lines starting with `-`, `*`, or `•`).

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |

**Returns:** `{"count": int}`

---

### `count_sections`
Count sections that begin with a given splitter word (e.g. `"Section"`).

| Parameter  | Type   | Required |
|------------|--------|----------|
| `text`     | string | yes      |
| `splitter` | string | yes      |

**Returns:** `{"count": int}`

---

### `count_capital_words`
Count words that are entirely in UPPERCASE (e.g. `NASA`, `IMPORTANT`).

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |

**Returns:** `{"count": int}`

---

### `check_starts_with_prompt`
Check that a text begins by repeating the original prompt exactly.

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |
| `prompt`  | string | yes      |

**Returns:** `{"passed": bool, "detail": str}`

---

### `check_quotation`
Check that a text is wrapped in double quotation marks.

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |

**Returns:** `{"passed": bool, "detail": str}`

---

### `check_json_format`
Check that a text is valid JSON.

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |

**Returns:** `{"passed": bool, "detail": str}`

---

### `count_paragraphs`
Count paragraphs (blocks of text separated by blank lines).

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |

**Returns:** `{"count": int}`

---

### `check_two_responses`
Check that a text contains two responses divided by `******`.

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |

**Returns:** `{"passed": bool, "detail": str}`

---

### `count_letter_frequency`
Count occurrences of a specific letter (case-insensitive).

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |
| `letter`  | string | yes      |

**Returns:** `{"count": int}`

---

### `check_ends_with`
Check that a text ends with an exact phrase.

| Parameter | Type   | Required |
|-----------|--------|----------|
| `text`    | string | yes      |
| `phrase`  | string | yes      |

**Returns:** `{"passed": bool, "detail": str}`
