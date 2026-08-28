# Sanitized AI-Triaged Samples

This folder contains 15 sanitized failure-triage examples for a capstone project.

## Provenance

The records are generalized from accepted AI triage findings in the local feedback ledger. The AI triage outcome is the annotation authority for this dataset; these are not represented as historical human verdicts.

## Privacy Boundaries

The samples retain only generic failure categories, abstract observations, AI pattern labels, and generic validation actions. They exclude original paths, environment names, seed names, model names, addresses, instruction values, ticket references, timestamps, and organization-specific identifiers.

## Format

`samples.jsonl` contains exactly 15 JSON objects, one per line. Each object has:

- `sample_id`: stable, non-source identifier.
- `failure_category`: generalized failure category.
- `observation`: sanitized triage observation.
- `ai_pattern_label`: accepted AI classification.
- `recommended_validation`: generic next diagnostic action.
- `annotation_authority`: always `ai_triage`.
- `annotation_status`: always `accepted_ai_triage`.
