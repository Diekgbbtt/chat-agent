# 12 - Mixed reply and part validator

**What to build:** One reply can carry a factual answer, a general answer, a capability limit, a refusal, a clarification, and a boundary, each tied to one verbatim.
The validator rejects missing, duplicated, or reordered parts.
The refusal part addresses exactly the unsafe types of its own verbatim.
No non-factual part states a graph fact or cites evidence.
No tool query contains a four-word sequence from a redacted verbatim.
The reply is joined in verbatim order.

**Blocked by:** 11.

**Status:** done

- [ ] A mixed safe plus unsafe request produces an answer part and a refusal part.
- [ ] A mixed safe plus out-of-scope request produces an answer part and a boundary part.
- [ ] A three-way mixed request produces answer, boundary, and refusal parts.
- [ ] An answer beside a blocked verbatim produces a clarification part.
- [ ] Missing, duplicated, and reordered parts are rejected.
- [ ] A wrong part kind is rejected.
- [ ] A non-factual part with evidence is rejected.
- [ ] A refusal with missing or extra safety types is rejected.
- [ ] A clarification with more than one question or a long quote is rejected.
- [ ] A tool query with redacted text is rejected.
- [ ] The composer produces ordered deterministic parts on second failure.
- [ ] Tests cover every combination and failure.
