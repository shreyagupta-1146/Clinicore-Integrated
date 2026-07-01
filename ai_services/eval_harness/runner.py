"""
ai_services/eval_harness/runner.py

CLI entry point for the safety eval harness.

Usage:
    python -m ai_services.eval_harness.runner --gold-set ai_services/eval_harness/gold_set/safety_cases.jsonl

Exit code 0 = all cases passed. Exit code 1 = at least one failure (use this
in CI to block merges that regress safety-validator behaviour).

This currently only runs SAFETY cases, because those are deterministic and
require no live infrastructure (no DB, no LLM, no network) — they are meant
to run on every PR in under a second. GROUNDING cases require a live
ClinicalReasoningService (real LLM call) and are intentionally NOT wired
into this fast path; see README "Eval Harness" section for the planned
nightly/pre-release grounding eval job.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Windows consoles default to a legacy codepage (cp1252) that can't encode the
# warning glyphs used below; force UTF-8 so the harness runs the same in CI
# (Linux, UTF-8 by default) and in a local Windows terminal.
if sys.stdout.encoding is not None and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from ai_services.eval_harness.schema import CaseResult, EvalReport, SafetyEvalCase
from ai_services.eval_harness.scorers import score_safety_case
from ai_services.guardrails.safety_validator import SafetyValidator


def load_safety_cases(path: Path) -> list[SafetyEvalCase]:
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_num}: invalid JSON — {exc}") from exc
            cases.append(SafetyEvalCase.model_validate(raw))
    return cases


def run(gold_set_path: Path) -> EvalReport:
    cases = load_safety_cases(gold_set_path)
    validator = SafetyValidator()

    results: list[CaseResult] = [score_safety_case(case, validator) for case in cases]
    unreviewed = sum(1 for c in cases if not c.clinician_reviewed)
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    return EvalReport(
        total_cases=total,
        passed=passed,
        failed=total - passed,
        pass_rate=(passed / total) if total else 0.0,
        results=results,
        unreviewed_case_count=unreviewed,
    )


def print_report(report: EvalReport) -> None:
    print(f"\n{'=' * 60}")
    print("CLINICAL SAFETY EVAL HARNESS — RESULTS")
    print(f"{'=' * 60}")
    for r in report.results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.case_id}")
        if not r.passed:
            print(f"         → {r.failure_reason}")
    print(f"{'-' * 60}")
    print(f"  Total:  {report.total_cases}")
    print(f"  Passed: {report.passed}")
    print(f"  Failed: {report.failed}")
    print(f"  Pass rate: {report.pass_rate:.1%}")
    print(f"  Unreviewed (non-clinician-signed-off) cases: {report.unreviewed_case_count}")
    if report.unreviewed_case_count > 0:
        print(
            "  ⚠️  This gold set has NOT been clinician-reviewed. "
            "Do NOT treat a green run as a clinical safety sign-off."
        )
    print(f"  Release-gate eligible: {report.is_release_gate_eligible}")
    print(f"{'=' * 60}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the clinical safety eval harness.")
    parser.add_argument(
        "--gold-set",
        type=Path,
        default=Path(__file__).parent / "gold_set" / "safety_cases.jsonl",
        help="Path to a JSONL gold-set file of SafetyEvalCase records.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write the full EvalReport as JSON (for CI artifact upload).",
    )
    args = parser.parse_args()

    report = run(args.gold_set)
    print_report(report)

    if args.json_out:
        args.json_out.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
