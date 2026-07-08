# Pull request

## What and why

<!-- What does this change and why? Link any issue. -->

## Checklist

- [ ] Ran the local gate (ruff, mypy, schema/import/link/plugin-sync checks, benchmark validate, pytest) and it's green.
- [ ] If I edited `core/`, I ran `python tools/sync_plugin.py` to refresh the vendored adapter copy.
- [ ] Any new provider statement carries a `clm-*` claim id in the Knowledge Engine.
- [ ] Contract changes are additive, or include a version bump + CHANGELOG entry.
- [ ] Updated tests for behavior changes.
- [ ] Updated docs (and CHANGELOG `[Unreleased]`) for user-, contract-, or knowledge-facing changes.
- [ ] No runtime network I/O added to shipped code; no weakening of the legitimacy gate or transformation rules.

## Notes for reviewers

<!-- Anything you want the reviewer to focus on. -->
