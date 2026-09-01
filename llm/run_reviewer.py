"""
run_reviewer.py

Runs the NovaPay LLM reviewer against a real evidence package or one of the
8 failure-mode test cases. Requires an ANTHROPIC_API_KEY environment
variable to actually call the API.

Usage:
    python run_reviewer.py --evidence evidence_novapay_real.json
    python run_reviewer.py --test-case B
    python run_reviewer.py --all-test-cases      # runs all 8, prints each
"""

import argparse
import json
import os
import sys

LLM_DIR = os.path.dirname(os.path.abspath(__file__))


def load_system_prompt():
    with open(os.path.join(LLM_DIR, "reviewer_system_prompt.md")) as f:
        return f.read()


def load_evidence(path):
    with open(path) as f:
        return json.load(f)


def load_test_case(case_id):
    with open(os.path.join(LLM_DIR, "test_cases.json")) as f:
        cases = json.load(f)["test_cases"]
    case = next((c for c in cases if c["id"] == case_id), None)
    if case is None:
        raise ValueError(f"No test case with id '{case_id}'. Valid ids: A-H")
    if "evidence" in case:
        return case["evidence"], case
    else:
        evidence_path = os.path.join(LLM_DIR, case["evidence_ref"])
        return load_evidence(evidence_path), case


def call_reviewer(evidence_dict, system_prompt):
    """Calls the Anthropic API with the system prompt + evidence package."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: pip install anthropic --break-system-packages")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: set ANTHROPIC_API_KEY environment variable first.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": f"Evidence package:\n\n{json.dumps(evidence_dict, indent=2)}\n\nReview this and produce the structured decision output."
        }],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--evidence", help="Path to an evidence package JSON file")
    group.add_argument("--test-case", help="Run a single test case (A-H)")
    group.add_argument("--all-test-cases", action="store_true", help="Run all 8 test cases")
    args = parser.parse_args()

    system_prompt = load_system_prompt()

    if args.evidence:
        evidence = load_evidence(args.evidence)
        print(f"=== Reviewing: {args.evidence} ===\n")
        print(call_reviewer(evidence, system_prompt))

    elif args.test_case:
        evidence, case = load_test_case(args.test_case.upper())
        print(f"=== Test Case {case['id']}: {case['name']} ===")
        print(f"Trap: {case['trap']}")
        print(f"Expected: {case['expected_correct_behavior']}\n")
        print(call_reviewer(evidence, system_prompt))

    elif args.all_test_cases:
        with open(os.path.join(LLM_DIR, "test_cases.json")) as f:
            cases = json.load(f)["test_cases"]
        for case in cases:
            evidence, _ = load_test_case(case["id"])
            print(f"\n{'=' * 60}\nTest Case {case['id']}: {case['name']}\n{'=' * 60}")
            print(f"Trap: {case['trap']}\n")
            print(call_reviewer(evidence, system_prompt))


if __name__ == "__main__":
    main()
