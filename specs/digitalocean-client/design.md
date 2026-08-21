# Design

## Overview

The package is two clients, not one, because DigitalOcean is two APIs with two
credentials. `DigitalOceanRestClient` owns the API v2 protocol — bearer token,
JSON, one request primitive — and delegates per-resource path composition to
api groups. `SpacesClient` owns the S3-compatible object store, which shares
nothing with the API v2 transport except this package: different host,
different credential, different auth scheme, different body format.

Neither subclasses `RestClientBase`. What the package preserves instead is the
`pydo` consumer contract — group attribute names, method names, keyword
spellings, and plain-`dict` responses — since `pydo` was removed from the
dependency tree while its call sites in `codecraftai-provisioning` stayed. The
one thing reused from `codecraftai-restclient-base` is `SigV4Signer`, which is
the piece with real cryptographic risk and which AWS needs identically.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  codecraftai-provisioning / venues / digitalocean          │
│  DigitalOceanClient                                        │
│    (unwraps DigitalOceanApiTokenCredential)                │
│  dopagination.collect_all_pages  (follows links.pages.next)│
└───────────────┬───────────────────────────┬────────────────┘
                │ API token                 │ Spaces key pair
                ▼                           ▼
┌──────────────────────────────┐  ┌──────────────────────────┐
│  DigitalOceanRestClient      │  │  SpacesClient            │
│    request()  ── bearer/JSON │  │    SigV4Signer (base)    │
│    .vpcs .firewalls .droplets│  │    path-style addressing │
│    .volumes .volume_actions  │  │    head/create/delete/   │
│    .ssh_keys .domains        │  │      list bucket         │
│         └── CollectionGroup  │  └────────────┬─────────────┘
└──────────────┬───────────────┘               │
               ▼                                ▼
   api.digitalocean.com/v2          {region}.digitaloceanspaces.com
```

---

## Module Layout

```
source/packages/ccai/restclient/digitalocean/
├── __init__.py
├── digitaloceanrestclient.py   # DigitalOceanRestClient
├── spacesclient.py             # SpacesClient
├── digitaloceanapierror.py     # DigitalOceanApiRequestError,
│                               #   SpacesRequestError
└── apigroups/
    ├── collectiongroup.py      # CollectionGroup
    ├── vpcgroup.py             # VpcGroup
    ├── firewallgroup.py        # FirewallGroup
    ├── dropletgroup.py         # DropletGroup
    ├── volumegroup.py          # VolumeGroup, VolumeActionGroup
    ├── sshkeygroup.py          # SshKeyGroup
    └── domaingroup.py          # DomainGroup
```

---

## Notable Choices

**Paging is the caller's, deliberately.** `CollectionGroup.list` returns one
page, exactly as the SDK did, and does not follow `links.pages.next`. The
traversal lives in the consumer as
`codecraftai-provisioning/venues/digitalocean/dopagination.collect_all_pages`.
Keeping it there means paging is visible at the call site rather than hidden
behind a method that sometimes issues one request and sometimes forty.

**Path-style Spaces addressing.** Requests go to
`https://{region}.digitaloceanspaces.com/{bucket}` rather than the
virtual-host form. A bucket created moments ago is immediately addressable by
path, while its virtual-host name has to wait on DNS — so an apply that
creates a bucket and then heads it would intermittently fail under
virtual-host addressing.

**The S3 error code is a first-class attribute.** `SpacesRequestError.code`
carries the parsed `<Code>` rather than leaving it inside a message string,
because callers branch on it: `NoSuchBucket` means "create it" and is
recovered, while an auth or throttle failure must stop the apply. The code is
matched on the element's *local* name at any depth, since whether a given
endpoint declares the XML namespace varies. A failed `HEAD` has no body at
all, so the HTTP status stands in — it must never come back empty for a 404.

**Two error types, not one hierarchy.** `DigitalOceanApiRequestError` carries
a `reason` (the API's `message`, prefixed by its `id`) and `SpacesRequestError`
carries a `code`. They are not related by inheritance because the two APIs
report failure in genuinely different vocabularies and a caller handling one
should not accidentally catch the other.

**Api groups are imported inside `__init__`.** The groups take the client as a
constructor argument and the client constructs the groups, so the imports are
deferred into `DigitalOceanRestClient.__init__` to break the cycle.

**Caller spelling wins over SDK spelling.** Where a consumer's keyword differed
from `pydo`'s, this package takes the consumer's — it is what defines the
contract now. The SDK's own irregularities are kept where consumers depend on
them: `droplets.destroy` rather than `delete`, and `/account/keys` as the SSH
key path even though the response key is `ssh_keys`.

---

## Error Model

- `DigitalOceanApiRequestError(status, reason, body)` — API v2 failures. The
  reason comes from the body's `message`, prefixed with its `id` when present,
  falling back to the HTTP reason phrase.
- `SpacesRequestError(status, code, body)` — Spaces failures. The code comes
  from the XML `<Code>`, falling back to the status as a string.

---

## See Also

- `codecraftai-restclient-base` — `ccai.restclient.base.awssigv4.SigV4Signer`,
  the reused signing implementation.
- `codecraftai-credentials` — `ccai.credentials.digitaloceanapitokencredential`,
  the credential type the consumer unwraps.
- `codecraftai-provisioning/venues/digitalocean/doclient.py` — the venue's
  `DigitalOceanClient`, which builds both clients and resolves the separate
  Spaces keys.
- `codecraftai-provisioning/venues/digitalocean/dopagination.py` — where the
  `links.pages.next` traversal lives.

---

## Testing Strategy

Tests live under
`source/testroots/testbase/ccai/tests/restclient/digitalocean/` and run
through the testbase runner, not pytest. A shared `fakesession.py` provides
the recording/replaying session injected on the `session=` seam of both
clients.

`test_digitaloceanrestclient.py` covers the transport (bearer header, `None`
parameter dropping, paging and filter forwarding, bodiless `204`, error reason
from `message` and its fallback) and then each group's addressing — collection
paths parametrized across groups, `/account/keys` specifically, the singular
response key on create, body pass-through, item-path deletes, `destroy` rather
than `delete` for droplets, ssh-key delete by id or fingerprint, firewall
update as a PUT, the volume actions sub-collection, and the zone-scoped record
paths.

`test_spacesclient.py` covers endpoint derivation and override, path-style
addressing, SigV4 signing (headers present, actually sent, distinct per
bucket), the bucket operations, and the error-code paths — parsed from XML,
read through a namespace, and falling back to the status for a bodiless or
unparseable failure, with an explicit test that an auth failure is not
reported as a missing bucket.

No DigitalOcean account is required for any test in the suite.
