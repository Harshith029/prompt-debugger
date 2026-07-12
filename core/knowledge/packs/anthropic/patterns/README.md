# Pattern Library (anthropic pack)

Before/after prompt patterns, indexed by [`index.json`](index.json). Each pattern is a markdown file mapping a rubric dimension and technique(s) to a concrete transformation.

**Status:** the index lists three seed patterns, each with an authored markdown body, all `status: draft`. The pattern library is expanded (more patterns, promotion to `active`) in M1 alongside the technique worked-examples. Every indexed `file` must exist on disk — enforced by `tests/test_knowledge_integrity.py`. Pattern bodies must respect the rewrite contract's transformation rules: a pattern may make intent more explicit, never less.
