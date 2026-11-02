# 07 - Guard gate and guard-only vertical slice

**What to build:** A natural-language message can run through normalisation, classification, validation, policy, and a complete reply in `guard_only` mode.
The bridge uses the legacy factual handler only for an answer handling and canonical text for every other part.
The legacy default is unchanged.

**Blocked by:** 05, 06.

**Status:** done

- [ ] `AGENT_MODE=guard_only` builds the new guard path.
- [ ] A safe in-scope request reaches the legacy factual handler.
- [ ] A safe out-of-scope request returns the canonical scope sentence.
- [ ] An unsafe request returns the canonical refusal.
- [ ] An invalid classification returns the canonical clarification.
- [ ] Raw SPARQL still bypasses the guard.
- [ ] A mixed request answers the answer handling and emits canonical text for the rest.
- [ ] The trace records classification, plan, and policy steps.
- [ ] Tests use a scripted guard client and the existing graph fixture.
- [ ] Legacy mode and all old tests stay green.
