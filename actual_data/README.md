# Sanitized Actual-Failure Sample

This folder contains one sanitized record derived from an actual reproducible validation failure.

The record retains only the observed failure category, a generic triage label, and a generic validation action. It excludes the original directory, test identifier, platform, environment tags, timestamps, tool names, error values, and all architecture-specific details.

`sample.json` is intentionally standalone and uses provenance fields that distinguish observed failure evidence from AI-triaged and human-labelled examples.

`sanitized_raw_error_extract.json` preserves the direct diagnostic structure and safe categorical/count values from the error record. Source-specific identifiers, addresses, selectors, seed data, and platform data are represented only by redaction tokens.
