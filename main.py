"""
Unified IFEval runner.

For every model installed in ollama, runs all tasks twice:
  - without skills (direct prompt)
  - with skills    (ReAct agent loop)

Prints a per-model comparison grid, then a final summary across all models.

  python main.py          # run everything
  python main.py no_skills
  python main.py skills
"""

import sys
import run_no_skills
import run_with_skills
import ifeval_loader

HF_TASK_COUNT    = 10   # number of real IFEval tasks to pull from HuggingFace
USE_CUSTOM_TASKS = False  # set True to re-enable hand-crafted tasks
PAUSED_MODELS    = {"llama3:8b", "qwen2.5:3b", "qwen3:1.7b"}


def get_models():
    return [m for m in run_no_skills.get_models() if m not in PAUSED_MODELS]


def build_tasks():
    hf_tasks = ifeval_loader.load_ifeval_tasks(n=HF_TASK_COUNT)
    custom   = run_no_skills.IFEVAL_TASKS if USE_CUSTOM_TASKS else []
    return custom + hf_tasks


# ── Grid helpers ───────────────────────────────────────────────────────────────

def _pad(s, w):
    return str(s)[:w].ljust(w)


def _hline(widths, left="├", mid="┼", right="┤", fill="─"):
    parts = [fill * (w + 2) for w in widths]
    print(left + mid.join(parts) + right)


def _row(widths, *cells):
    parts = [f" {_pad(c, w)} " for c, w in zip(cells, widths)]
    print("│" + "│".join(parts) + "│")


# ── Per-model comparison grid ──────────────────────────────────────────────────

def print_model_grid(model: str, no_skill: dict, with_skill: dict, tasks: list):
    """Side-by-side no-skills vs with-skills for one model."""
    W_TASK   = 8
    W_CONSTR = 42
    W_COL    = 16
    widths   = [W_TASK, W_CONSTR, W_COL, W_COL]
    total    = sum(widths) + len(widths) * 3 + 1

    print()
    print("┌" + "─" * (total - 2) + "┐")
    print("│" + f"  {model}".ljust(total - 2) + "│")
    _hline(widths, "├", "┬", "┤")
    _row(widths, "Task", "Constraint", "No Skills", "With Skills")
    _hline(widths, "├", "┼", "┤")

    for task in tasks:
        tid = task["id"]
        p0, d0 = no_skill[tid]
        p1, d1 = with_skill[tid]
        _row(
            widths,
            tid,
            task["constraint"],
            f"{'PASS' if p0 else 'FAIL'}  {d0}"[:W_COL],
            f"{'PASS' if p1 else 'FAIL'}  {d1}"[:W_COL],
        )

    n  = len(tasks)
    s0 = sum(1 for t in tasks if no_skill[t["id"]][0])
    s1 = sum(1 for t in tasks if with_skill[t["id"]][0])
    _hline(widths, "├", "┼", "┤")
    _row(widths, "", "Score",
         f"{s0}/{n} ({int(100*s0/n)}%)",
         f"{s1}/{n} ({int(100*s1/n)}%)")
    print("└" + "─" * (total - 2) + "┘")


# ── Summary grid ───────────────────────────────────────────────────────────────

def print_summary_grid(all_results: dict, tasks: list):
    """One row per model, columns: no-skills score | with-skills score."""
    W_MODEL = 20
    W_COL   = 16
    widths  = [W_MODEL, W_COL, W_COL]
    total   = sum(widths) + len(widths) * 3 + 1
    n       = len(tasks)

    print()
    print("┌" + "─" * (total - 2) + "┐")
    print("│" + "Summary — All Models".center(total - 2) + "│")
    _hline(widths, "├", "┬", "┤")
    _row(widths, "Model", "No Skills", "With Skills")
    _hline(widths, "├", "┼", "┤")

    for model, (no_skill, with_skill) in all_results.items():
        s0 = sum(1 for t in tasks if no_skill[t["id"]][0])
        s1 = sum(1 for t in tasks if with_skill[t["id"]][0])
        _row(widths, model,
             f"{s0}/{n} ({int(100*s0/n)}%)",
             f"{s1}/{n} ({int(100*s1/n)}%)")

    print("└" + "─" * (total - 2) + "┘")
    print()


# ── Main runner ────────────────────────────────────────────────────────────────

def run_all():
    models = get_models()
    tasks  = build_tasks()
    print(f"\nModels found : {models}")
    print(f"Tasks loaded : {len(tasks)} ({len(run_no_skills.IFEVAL_TASKS)} custom + {len(tasks) - len(run_no_skills.IFEVAL_TASKS)} from HuggingFace)\n")

    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    all_results = {}  # {model: (no_skill_dict, with_skill_dict)}

    for model in models:
        print(f"\n{'━'*60}")
        print(f"  {model}")
        print(f"{'━'*60}")

        if mode in ("no_skills", "both"):
            print("\n  [without skills]")
            no_skill = run_no_skills.evaluate(model, tasks)
        else:
            no_skill = {t["id"]: (False, "skipped") for t in tasks}

        if mode in ("skills", "both"):
            print("\n  [with skills]")
            with_skill = run_with_skills.evaluate(model, tasks)
        else:
            with_skill = {t["id"]: (False, "skipped") for t in tasks}

        all_results[model] = (no_skill, with_skill)

    print("\n" + "═" * 60)
    print("  Results")
    print("═" * 60)

    for model, (no_skill, with_skill) in all_results.items():
        print_model_grid(model, no_skill, with_skill, tasks)

    print_summary_grid(all_results, tasks)


if __name__ == "__main__":
    run_all()
