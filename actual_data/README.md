# Sanitized Actual Failure Input

This directory contains a small, generic input representation of one real validation failure for the TriageMate capstone demonstration.

The record excludes source paths, hostnames, build and platform names, seeds, timestamps, internal product and tool names, ticket references, user names, and raw logs. It retains only sanitized failure metadata and observed flow outcomes needed to test the triage prompt.

No human label, confidence, rationale, recommendation, or other post-processing result is included. The triage system must classify the input from the observed evidence and apply the human checkpoint described in the playbook.
