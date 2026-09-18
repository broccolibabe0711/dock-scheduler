# 7. Inputs are validated where they enter, so the rules can trust them

**Context.** A review of the first rules engine found that a berth built with the string "exclusive" instead of the enum, or a vessel with a NaN or negative length, silently passed every rule and returned OK. Rows come out of SQLite as strings and numbers, and JSON accepts NaN.

**Decision.** `Berth`, `Vessel` and `Reservation` coerce enums and check that lengths are finite and positive in `__post_init__`; the API's request models refuse non-finite and non-positive numbers; the SQLite schema repeats the same constraints as CHECKs. The rules compare with `is` on real enums and never see a value they cannot trust.

**Consequences.** Bad data fails loudly at construction with a message naming the field, in every entry path. The tests include the exact scenarios from the review.
