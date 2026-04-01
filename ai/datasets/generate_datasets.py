"""
Purpose:
- Programmatically generate training datasets for language AI workflows.
- Produce three dataset categories:
  1) Correct programs
  2) Incorrect programs
  3) Optimized vs non-optimized pairs

Large-scale generation uses many template variants and compact JSON output.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Callable, Dict, List


BASE_DIR = Path(__file__).parent
OUTPUT_FILES = {
    "correct": BASE_DIR / "correct_programs.json",
    "incorrect": BASE_DIR / "incorrect_programs.json",
    "optimized_pairs": BASE_DIR / "optimized_pairs.json",
}


def _r(a: int, b: int) -> int:
    return random.randint(a, b)


def _correct_program_samples(count: int) -> List[Dict[str, str]]:
    """Many templates so large datasets stay diverse."""

    def t1() -> str:
        x, y = _r(1, 99), _r(1, 99)
        return f"var a = {x}\nvar b = {y}\nvar c = a + b\n"

    def t2() -> str:
        x, y = _r(1, 50), _r(1, 20)
        return f"var n = {x}\nwhen n > {y} {{ var out = n - 1 }} otherwise {{ var out = 0 }}\n"

    def t3() -> str:
        m, k = _r(1, 40), _r(1, 15)
        return f"var m = {m}\nvar p = m * {k}\nvar q = p + 2\n"

    def t4() -> str:
        a, b, c = _r(1, 30), _r(1, 30), _r(1, 10)
        return f"var x = {a}\nvar y = {b}\nvar z = x * y + {c}\n"

    def t5() -> str:
        n, t = _r(5, 60), _r(1, 9)
        return f"var n = {n}\nwhen n < {t} {{ var r = 0 }} otherwise {{ var r = n - {t} }}\n"

    def t6() -> str:
        a, b = _r(1, 25), _r(1, 25)
        return f"var a = {a}\nvar b = {b}\nvar s = (a + b) * 2\n"

    def t7() -> str:
        x, y = _r(1, 40), _r(1, 40)
        return f"var x = {x}\nwhen x == {y} {{ var eq = 1 }} otherwise {{ var eq = 0 }}\n"

    templates: List[Callable[[], str]] = [t1, t2, t3, t4, t5, t6, t7]
    samples: List[Dict[str, str]] = []
    for i in range(count):
        program = random.choice(templates)()
        samples.append({"id": f"correct_{i+1}", "code": program})
    return samples


def _incorrect_program_samples(count: int) -> List[Dict[str, str]]:
    """Broken snippets: lexer/parser/semantic failure modes."""

    def bad1() -> str:
        x = _r(1, 50)
        return f"var a {x}\n"

    def bad2() -> str:
        x = _r(1, 50)
        return f"var 1name = {x}\n"

    def bad3() -> str:
        x = _r(1, 50)
        return f"var a = {x} +\n"

    def bad4() -> str:
        y = _r(1, 20)
        return f"when a > {y} {{ var b = 1 \n"

    def bad5() -> str:
        x = _r(1, 50)
        return f"var a = b + {x}\n"

    def bad6() -> str:
        return "var x = \n"

    def bad7() -> str:
        return "when { var x = 1 }\n"

    def bad8() -> str:
        return "var x = 1 + + 2\n"

    templates = [bad1, bad2, bad3, bad4, bad5, bad6, bad7, bad8]
    samples: List[Dict[str, str]] = []
    for i in range(count):
        program = random.choice(templates)()
        samples.append({"id": f"incorrect_{i+1}", "code": program})
    return samples


def _optimized_pairs_samples(count: int) -> List[Dict[str, str]]:
    samples: List[Dict[str, str]] = []
    for i in range(count):
        x, y = _r(1, 40), _r(1, 40)
        z = x + y
        non_opt = (
            f"var a = {x}\n"
            f"var b = {y}\n"
            "var t = a + b\n"
            "var out = t\n"
        )
        optimized = f"var out = {z}\n"
        samples.append(
            {
                "id": f"opt_pair_{i+1}",
                "non_optimized": non_opt,
                "optimized": optimized,
                "optimization_note": "constant_folding",
            }
        )
    return samples


def generate_datasets(count_per_category: int, compact: bool = True) -> Dict[str, int]:
    """Write JSON files. Use compact=True for large files (smaller disk, faster I/O)."""
    correct = _correct_program_samples(count_per_category)
    incorrect = _incorrect_program_samples(count_per_category)
    optimized_pairs = _optimized_pairs_samples(count_per_category)

    indent = None if compact else 2
    separators = (",", ":") if compact else (", ", ": ")

    def dump(data: object, path: Path) -> None:
        path.write_text(
            json.dumps(data, indent=indent, ensure_ascii=False, separators=separators),
            encoding="utf-8",
        )

    dump(correct, OUTPUT_FILES["correct"])
    dump(incorrect, OUTPUT_FILES["incorrect"])
    dump(optimized_pairs, OUTPUT_FILES["optimized_pairs"])

    return {
        "correct_programs": len(correct),
        "incorrect_programs": len(incorrect),
        "optimized_pairs": len(optimized_pairs),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate language AI datasets.")
    parser.add_argument(
        "--count",
        type=int,
        default=8000,
        help="Samples per category (correct, incorrect, optimized_pairs). Default 8000.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON (much larger files). Default is compact.",
    )
    args = parser.parse_args()
    summary = generate_datasets(count_per_category=args.count, compact=not args.pretty)
    print("language datasets generated:", summary)


if __name__ == "__main__":
    main()
