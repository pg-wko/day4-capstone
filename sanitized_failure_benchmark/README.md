# Sanitized Failure Benchmark

This directory contains 15 small, generic failure samples for the TriageMate capstone playbook. The samples are derived from the 15 unique failure folders supplied for this exercise; one duplicated source path was omitted.

## Files

- `failures.jsonl`: one JSON record per failure, including evidence and a human-label field.
- `ground_truth.csv`: the sample ID and label index for quick scoring.

## Notes

- `error_type` / `error_message` are intentionally generic and repeat across samples in the same bucket (e.g. all "unexpected_exception" samples share identical text). The true category is only recoverable from `evidence` — this mirrors the real-world trap where surface error text looks alike but the root cause differs.
- Labels: `PRODUCT_BUG`, `TEST_FAILURE`, `ENVIRONMENT`, `KNOWN_FLAKE`, `INSUFFICIENT_EVIDENCE`.
- `human_label_confidence` in `ground_truth.csv` is one of `high`, `medium`, `low`, reflecting how clear-cut the human labeller judged the evidence to be.
