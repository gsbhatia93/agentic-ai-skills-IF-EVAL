"""
Entry point — runs both IFEval evaluations and prints their grids back to back.

  python main.py            # runs both
  python main.py no_skills  # runs only the no-skills version
  python main.py skills     # runs only the with-skills version
"""

import sys
import run_no_skills
import run_with_skills


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"

    if mode in ("no_skills", "both"):
        print("\n" + "━" * 60)
        print("  Part 1 — Without Skills")
        print("━" * 60)
        run_no_skills.run_all()

    if mode in ("skills", "both"):
        print("\n" + "━" * 60)
        print("  Part 2 — With Skills (ReAct agent loop)")
        print("━" * 60)
        run_with_skills.run_all()


if __name__ == "__main__":
    main()
