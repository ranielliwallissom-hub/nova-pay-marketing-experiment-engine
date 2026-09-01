# Manual Verification Log

The sandbox this project was built in has no ANTHROPIC_API_KEY available, so
`run_reviewer.py` could not be exercised against the live API during
development. Instead, the system prompt was manually verified by having
Claude (the same model family the script calls) act as the reviewer against
3 of the 8 test cases, reasoning through the rules by hand.

## Test Case B -- structural power floor (Rule 2)
Result: GATHER MORE EVIDENCE / MODERATE / WEAK-TO-MODERATE / ATTRACTIVE
Correctly named the 1/N structural floor (p=0.20 with N=5) instead of
reading it as "no effect."

## Test Case E -- excellent fit, undocumented selection (Rule 5)
Result: GATHER MORE EVIDENCE / MODERATE / STRONG / ATTRACTIVE
This is the sharpest test of the design: RMSE=0.8, p=0.033, 30-unit donor
pool -- every surface signal says STRONG. Causal validity was still capped
at MODERATE purely because `treatment_selection_documented=false`,
independent of fit quality. This is the exact failure mode a naive reviewer
(or a naive first-pass human read) falls into.

## Test Case H -- positive control
Result: SCALE / STRONG / STRONG / ATTRACTIVE
No caveats manufactured. Confirms the reviewer isn't just reflexively
cautious -- it can recognize genuinely clean evidence and say so plainly.

## Test Case F -- real NovaPay data, cross-checked
Running the real evidence package through this system prompt reproduces
the same verdict (GATHER MORE EVIDENCE / MODERATE / WEAK-TO-MODERATE /
UNCERTAIN) that was derived by hand, independently, earlier in the project
-- before this system prompt existed. That agreement is the strongest
available evidence the encoded rules match the actual reasoning process,
not just a plausible-sounding prompt.

## Known limitation
Test Cases A, C, D, G were schema-validated but not manually walked through
turn-by-turn like B/E/H above. Before relying on this reviewer for a live
demo, run `python run_reviewer.py --all-test-cases` with a real API key and
check each output against `expected_correct_behavior` in test_cases.json.
