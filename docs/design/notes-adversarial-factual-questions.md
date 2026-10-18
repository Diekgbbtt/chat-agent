Some adversarial questions types that require specific handling with regex expressions:
1. Negotiations: For example, using no / not in the question cannot be comprehended by our model at the moment.
2. Subventions: domain entities containing other domain entities(such as title containing other short titles or same for directors). For example, "Up" which is in the knowledge graph and "Don't Look Up" which is not. So, when the question is who directed "Don't Look Up" instead of the "I don't know" answer, the answer returned is the director of Up.
3. Sparse entities formating -- not all entities that parametrise the SPRQL query are enclosed in citation marks.
4. Minimal entitiy spelling mistakes -- that should still be mappped to a non-mispelled query and therfore retrieve the relevant content
5. Partial Entity value specifications -- rather than mentioning the full film name, only the core name is mentioned, e.g. The Handmaiden --> handmaiden


### High level natural language generation workflow for fully symbolic model
1. Entity recognition: find the mention (“The Handmaiden”) → slot filling
2. Entity linking: map the mention to a graph node
3. Relation detection: map the question to a graph property (“wrote the screenplay” is “screenwriter”) → intent classification
4. Query construction: fill or generate a SPARQL query, depending on whether the head or the tail of the triple is missing
5. Validation: check that the query is valid and its results have the expected type (“who” should be answered with a person)
6. Answer generation: verbalize the result (“Jeong Seo-kyeong and Park Chan-wook”) → NLG

- adversarial note: which assumptions on the data items at the data contracts between each phase(and from source->phase1 and last-phase-> output) might be done?

