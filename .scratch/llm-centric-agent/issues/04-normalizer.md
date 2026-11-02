# 04 - Input normalizer

**What to build:** Every message reaches the guard as one normalised string.
The normaliser trims, caps length, repairs curly quotes, and strips the course prefix.
Discrimination spans and relationship entities refer to the normalised string.

**Blocked by:** None - can start immediately.

**Status:** done

- [ ] The normaliser trims leading and trailing whitespace.
- [ ] The normaliser caps input at the existing maximum.
- [ ] The normaliser maps curly quotes to straight quotes.
- [ ] The normaliser strips the course prefix case-insensitively.
- [ ] The normaliser keeps all other text unchanged.
- [ ] Tests cover each rule and idempotence.
