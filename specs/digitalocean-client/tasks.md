# Implementation Plan — DigitalOcean Client

## Package Skeleton

- [x] 1. Create `source/packages/ccai/restclient/digitalocean/` with the API v2 client, the Spaces client, the error module, and an `apigroups/` subpackage.
- [x] 2. Take SigV4 signing from `codecraftai-restclient-base` rather than vendoring a signer.

## API v2 Transport

- [x] 3. Implement `DigitalOceanRestClient` applying the bearer token and `Accept` as session-level headers, with an injectable `session` and a `base_url` override.
- [x] 4. Construct the seven api groups as public attributes, deferring their imports into `__init__` to break the client/group cycle.
- [x] 5. Implement `request()` with `None`-parameter dropping, JSON body encoding, a 60-second default timeout, and a per-request override.
- [x] 6. Decode an empty body to `{}` for `204` deletes, an undecodable body to `{}`, and a non-object body to `{"data": ...}`.
- [x] 7. Implement `_extract_error_reason` reading `message` prefixed by `id`, falling back to the HTTP reason phrase, and `DigitalOceanApiRequestError` carrying status, reason, and raw body.

## Api Groups

- [x] 8. Implement `CollectionGroup` with `COLLECTION_PATH`, single-page `list(per_page=, page=, **filters)`, `create(body=)`, and `_delete_by_id`.
- [x] 9. Implement `VpcGroup` at `/vpcs` and `VolumeGroup` at `/volumes`.
- [x] 10. Implement `FirewallGroup` at `/firewalls` with `update` as a full-replacement PUT to the item path.
- [x] 11. Implement `DropletGroup` at `/droplets` with `destroy`, matching the API's verb rather than renaming it to `delete`.
- [x] 12. Implement `VolumeActionGroup` posting to `/volumes/{id}/actions` with the verb in the body.
- [x] 13. Implement `SshKeyGroup` at `/account/keys`, accepting either the id or the fingerprint on delete.
- [x] 14. Implement `DomainGroup` with zone-scoped record list, create, and delete under `/domains/{name}/records`.

## Spaces

- [x] 15. Implement `SpacesClient` building a `SigV4Signer` scoped to the `s3` service and the client's region, with an endpoint derived from the region template and an `endpoint_url` override.
- [x] 16. Address buckets path-style so a freshly created bucket is reachable without waiting on DNS.
- [x] 17. Implement `head_bucket`, `create_bucket`, `delete_bucket`, and `list_buckets` with the capitalised `Bucket` keyword.
- [x] 18. Implement `_local_name` / `_iter_local` so namespaced and un-namespaced S3 bodies read alike.
- [x] 19. Implement `_extract_error_code` reading the first `<Code>` at any depth, falling back to the status for bodiless and unparseable failures.
- [x] 20. Implement `SpacesRequestError` carrying the S3 code as a first-class attribute.

## Tests

- [x] 21. Implement the shared `fakesession.py` recording/replaying session.
- [x] 22. Transport tests: bearer header, `None` parameter dropping, paging and filter forwarding, bodiless `204`, error reason and its fallback.
- [x] 23. Addressing tests parametrized across the collections, plus `/account/keys`, item-path deletes, `destroy` for droplets, ssh-key delete by id or fingerprint, and the firewall PUT.
- [x] 24. Create tests: singular response key, body passed through unchanged.
- [x] 25. Volume-action and zone-scoped DNS record path tests.
- [x] 26. Spaces tests: endpoint derivation and override, path-style addressing, signing present/sent/distinct-per-bucket, the four bucket operations.
- [x] 27. Spaces error tests: code from XML, code through a namespace, status fallback for bodiless and unparseable bodies, and an explicit test that an auth failure is not reported as a missing bucket.
- [x] 28. Migrate the suite from pytest to testbase (`testbase.raises`, `testbase.parametrize`).

## Open Items

- [ ] 29. No method accepts an `aspects` parameter, which the repository coding standard requires of every behaviour-bearing method. Retry, backoff, and timeout policy are not caller-controlled beyond constructor arguments.
- [ ] 30. Both clients accept raw secret material — a token string on `DigitalOceanRestClient`, an access-key pair on `SpacesClient` — rather than a typed credential from `codecraftai-credentials`. Unwrapping happens one layer up in the venue's `DigitalOceanClient` (`codecraftai-provisioning/venues/digitalocean/doclient.py`).
- [ ] 31. No retry or rate-limit handling. DigitalOcean answers `429` with `RateLimit-*` headers that nothing here reads, so a throttled call fails as a plain `DigitalOceanApiRequestError`.
- [ ] 32. `IDENTIFIER_KEYWORD` is declared on `CollectionGroup` and set on all five regular collections, but no code reads it — each group spells its own delete keyword out. Either wire it into a generic `delete` or drop it; as written it is documentation that cannot go stale visibly.
- [ ] 33. `DigitalOceanRestClient` mutates the headers of an injected session rather than sending auth per request. A session shared with another client would silently acquire this client's `Authorization` header.
- [ ] 34. Spaces covers bucket-level operations only. Object put, get, list, and delete are not implemented, though they would run over the same signed transport.
- [ ] 35. No property-based tests. `ccai.testbase.properties` is available; the Spaces error-code extraction is the natural candidate, since it must never yield an empty code for a 404 across arbitrary body shapes.
- [ ] 36. The repository's `AGENTS.md` states that `digitaloceanrestclient` handles "cursor paging"; it does not, by design — the traversal lives in the consumer's `dopagination.collect_all_pages`. The overview should be corrected.
- [ ] 37. No live-API smoke tier. Every test runs against the fake session.
