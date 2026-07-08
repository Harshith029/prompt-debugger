---
name: Claim re-verification
about: Quarterly check that Knowledge Engine claims still match their public sources
title: "Claim re-verification: <quarter>"
labels: knowledge, verification
---

## Scope

Re-verify every active claim in the Knowledge Engine against its source URL. This keeps the taxonomy and techniques honest as provider documentation evolves (see docs/ROADMAP.md → Continuous).

## Checklist

- [ ] For each claim in `core/knowledge/packs/*/claims.json`, open its `url` and confirm the `claim` text still holds.
- [ ] Update `last_verified` to today's date for claims that still hold; set `status: verified`.
- [ ] For claims whose source changed, set `status: stale` and open a follow-up to revise the dependent taxonomy/technique entries.
- [ ] For claims no longer supported by any source, set `status: retired` and revise or remove dependents.
- [ ] Resolve any CI warnings about active entries citing non-active claims.
- [ ] Bump the pack/knowledge version and add a CHANGELOG entry if content changed.

## Notes

<!-- Record anything notable: doc URLs that moved, wording that shifted, new event kinds observed. -->
