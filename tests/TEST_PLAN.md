# Test plan — write these yourself

Seven are done in `test_ledger_rules.py`. These are the remaining cases that take
the suite past 25 and, more importantly, cover the things a reviewer will poke at.
Write them in your own words — the test names are the part people read.

## `test_balances.py` — derived balances (needs `db`)
- [ ] A new account has a balance of zero.
- [ ] One entry of 150.00 leaves the debit account at +15000 and the credit account at -15000.
- [ ] Three entries against one account sum correctly.
- [ ] Deleting an entry moves the balance back (cascade removes its postings).
- [ ] `trial_balance` is zero after a run of random valid entries.

## `test_entries_api.py` — HTTP layer
- [ ] POST /entries with balanced postings returns 201 and the entry id.
- [ ] POST /entries with unbalanced postings returns 400 and does not write anything.
- [ ] POST /entries referencing an unknown account code returns 404.
- [ ] A rejected entry leaves the account balances untouched (the rollback actually works).
- [ ] `external_id` is unique: posting the same one twice returns a conflict.

## `test_idempotency.py` — the headline feature
- [ ] Same key, same body, twice: one entry created, both responses identical.
- [ ] The replayed response carries the `Idempotent-Replay` header.
- [ ] Same key, different body: 409.
- [ ] Two different keys with the same body: two entries. (Idempotency is per key, not per payload.)
- [ ] No key at all: the endpoint still works, and repeats create separate entries.
- [ ] Concurrent requests with one key create exactly one entry. Use two threads and
      two sessions; the unique constraint is what saves you, not the read.

## `test_webhooks.py`
- [ ] First delivery of an event id is accepted.
- [ ] Re-delivering the same id returns `duplicate` and creates no second row.
- [ ] The same event id from a different provider is not treated as a duplicate.
- [ ] An event with no id is ignored rather than crashing.

## `test_auth.py`
- [ ] No Authorization header: 403 from the bearer scheme.
- [ ] Malformed token: 401.
- [ ] Expired token: 401 with a message about expiry.
- [ ] A `service` role token cannot create an account (admin only): 403.
- [ ] A `service` role token can post a payment: 201.

## Worth adding if you have time
- [ ] A property test with Hypothesis: any list of amounts that sums to zero validates.
- [ ] A concurrency test posting to the same account from several threads, asserting
      the trial balance is still zero afterwards.
