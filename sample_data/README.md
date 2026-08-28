# Sanitized Failure Benchmark

This directory contains 15 small, generic failure samples for the TriageMate capstone playbook. The samples are derived from the 15 unique failure folders supplied for this exercise; one duplicated source path was omitted.

## Files

- `failures.jsonl`: one JSON record per failure, including evidence and a human-label field.
- `ground_truth.csv`: the sample ID and label index for quick scoring.

## Label taxonomy

The labels match the playbook prompt:

- `PRODUCT_BUG`: deterministic evidence points to incorrect implementation behavior or a repeatable execution failure.
- `TEST_DEFECT`: the test or oracle is shown to be wrong.
- `ENVIRONMENT`: infrastructure, service, credential, network, or setup evidence explains the failure.
- `KNOWN_FLAKE`: an explicit historical record identifies the same failure pattern as flaky.
- `INSUFFICIENT_EVIDENCE`: the available evidence does not safely distinguish the other categories.

These are conservative analyst labels based on compact failure metadata. They should receive domain-owner confirmation before being presented as final benchmark ground truth. No `KNOWN_FLAKE` label is used without an explicit historical match, and no test or environment label is invented where the source evidence does not support it.

## Sanitization boundary

The dataset intentionally excludes raw logs, binary dumps, source paths, build and board names, seeds, memory addresses, hostnames, usernames, internal versions, ticket IDs, and proprietary file names. The evidence text is rewritten into generic terms while preserving the diagnostic shape needed for classification.

## Suggested use

Feed each JSONL record into the playbook prompt as the test, failure, stack trace, service log, code-change, and history evidence. Score the model's `category` against `human_label`, and require abstention when the evidence is ambiguous.
