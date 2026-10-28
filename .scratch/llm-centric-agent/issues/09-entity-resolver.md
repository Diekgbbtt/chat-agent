# 09 — Entity resolver tool

**What to build:** The QA model can turn a label into candidate QIDs.
The resolver returns candidate QIDs, labels, types, film or human flags, and degree.
It performs exact, prefix, and contains lookup and never fuzzy matching.
The lexicon exposes the sorted prefix index the resolver needs.

**Blocked by:** 08.

**Status:** ready-for-agent

- [ ] Exact matches come before prefix matches, and prefix matches before contains matches.
- [ ] Each candidate carries QID, label, types, film flag, human flag, and degree.
- [ ] The result limit is enforced.
- [ ] A missing label returns an empty candidate list.
- [ ] Fuzzy matching is absent.
- [ ] The lexicon builds a sorted label list at startup.
- [ ] Tests use the existing graph fixtures and cover every match class.
