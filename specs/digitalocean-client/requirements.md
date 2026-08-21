# Requirements

## Introduction

The `digitalocean-client` feature provides a pure-Python client for the two
APIs a DigitalOcean venue needs, without depending on the `pydo` SDK or an S3
SDK.

They are deliberately two transports rather than one, because they are two
different protocols with two different credentials. `DigitalOceanRestClient`
speaks the DigitalOcean API v2 — plain REST over HTTPS, JSON bodies, a Bearer
personal access token — and covers VPCs, firewalls, droplets, volumes and
volume actions, SSH keys, and domains with their DNS records. `SpacesClient`
speaks Spaces, DigitalOcean's S3-compatible object store, which authenticates
with SigV4 using an access-key pair separate from the API token; the signing
algorithm is reused from `ccai.restclient.base.awssigv4` because it is
identical to the one AWS needs.

The api groups and their keyword names match the surface `pydo` presented —
`vpcs`, `firewalls`, `droplets`, `volumes`, `volume_actions`, `ssh_keys`,
`domains`, called as `list(per_page=, page=)`, `create(body=)`,
`delete(vpc_id=)` — and responses are plain `dict`s, because that is how
consumer code already reads them. This package is consumed by
`codecraftai-provisioning/venues/digitalocean/` through its
`DigitalOceanClient`, which is where a `DigitalOceanApiTokenCredential` is
unwrapped into the token and Spaces keys this package accepts.

---

## Requirements

### Requirement 1: Authenticate Against the DigitalOcean API v2

**User Story:** As a venue provisioner, I want API requests carrying a bearer
token so that every operation runs as the intended account.

#### Acceptance Criteria

1. WHEN `DigitalOceanRestClient` is constructed with a token THE SYSTEM SHALL
   set `Authorization: Bearer <token>` and `Accept: application/json` as
   session-level headers applied to every request.
2. THE SYSTEM SHALL default the base URL to `https://api.digitalocean.com/v2`
   and SHALL accept a `base_url` override, trimming any trailing slash.
3. THE SYSTEM SHALL expose the api groups as public attributes named `vpcs`,
   `firewalls`, `droplets`, `volumes`, `volume_actions`, `ssh_keys`, and
   `domains`.

### Requirement 2: Perform API v2 Requests

**User Story:** As an api group, I want one request primitive that handles
encoding, timeouts, and decoding so that each group only composes a path and a
body.

#### Acceptance Criteria

1. WHEN `request(method, path, params, body)` is invoked THE SYSTEM SHALL
   compose the URL from the base URL and path and return the decoded JSON
   body.
2. THE SYSTEM SHALL drop query parameters whose value is `None`, so that an
   unset page size is simply absent from the request rather than sent as null.
3. WHEN a body is supplied THE SYSTEM SHALL serialise it as JSON and set
   `Content-Type: application/json`.
4. WHEN the response carries no body THE SYSTEM SHALL return an empty dict —
   deletes answer `204`.
5. WHEN the response body is not decodable as JSON THE SYSTEM SHALL return an
   empty dict rather than raising.
6. WHEN the decoded body is not an object THE SYSTEM SHALL return it wrapped
   as `{"data": <decoded>}`.
7. THE SYSTEM SHALL apply a default 60-second timeout and accept a
   per-request override.

### Requirement 3: Report API v2 Failures With the API's Own Message

**User Story:** As a consumer, I want the API's error message rather than the
bare HTTP phrase so that a failure says what is actually wrong.

#### Acceptance Criteria

1. WHEN a response status is outside `200..299` THE SYSTEM SHALL raise
   `DigitalOceanApiRequestError` carrying `status`, `reason`, and the raw
   `body`.
2. WHEN the failed body carries a `message` THE SYSTEM SHALL use it as the
   reason, prefixed with the body's `id` when one is present.
3. WHEN the failed body is absent, not JSON, not an object, or carries no
   `message` THE SYSTEM SHALL fall back to the HTTP reason phrase.
4. THE SYSTEM SHALL include the method, path, status, and reason in the
   exception's human-readable text.

### Requirement 4: Provide the Regular Collections Through One Shape

**User Story:** As a maintainer, I want the uniform collections written once so
that each resource type declares only what differs.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide `CollectionGroup` deriving its behaviour from a
   `COLLECTION_PATH` class attribute.
2. WHEN `list(per_page=, page=, **filters)` is invoked THE SYSTEM SHALL GET
   the collection path forwarding paging parameters and any further filters
   such as `tag_name`.
3. THE SYSTEM SHALL return ONE page from `list`, exactly as the SDK did,
   leaving `links.pages.next` traversal to the caller.
4. WHEN `create(body=)` is invoked THE SYSTEM SHALL POST the body through
   unchanged and return the response carrying the resource under the
   collection's singular key.
5. THE SYSTEM SHALL delete by composing `{COLLECTION_PATH}/{identifier}`.

### Requirement 5: Cover the Venue's Resource Types

**User Story:** As a provisioner, I want the resource types the venue
provisions, spelled the way callers already spell them.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide `VpcGroup` at `/vpcs` with `delete(vpc_id=)`.
2. THE SYSTEM SHALL provide `FirewallGroup` at `/firewalls` with
   `update(firewall_id=, body=)` issued as a PUT to the item path, and
   `delete(firewall_id=)`. THE PUT is a full replacement rather than a
   merge — omitted rules are removed — so the body must describe the
   firewall's complete desired state.
3. THE SYSTEM SHALL provide `DropletGroup` at `/droplets` with
   `destroy(droplet_id=)` — named `destroy` rather than `delete`, matching the
   API and the SDK.
4. THE SYSTEM SHALL provide `VolumeGroup` at `/volumes` with
   `delete(volume_id=)`.
5. THE SYSTEM SHALL provide `SshKeyGroup` at `/account/keys` — SSH keys belong
   to the account rather than to any one resource — and its
   `delete(ssh_key_id=)` SHALL accept either the numeric id or the key
   fingerprint, both of which the API honours in that position.

### Requirement 6: Post Volume Actions

**User Story:** As a provisioner attaching storage, I want attach and detach
expressed as the API expresses them.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide `VolumeActionGroup.post_by_id(volume_id=, body=)`
   posting to `/volumes/{volume_id}/actions`.
2. THE SYSTEM SHALL name the verb inside the body's `type` field rather than
   in the path, which is how the API models attach and detach.
3. THE SYSTEM SHALL return the decoded response carrying the action record
   under `action`.

### Requirement 7: Manage Domains and DNS Records

**User Story:** As a provisioner publishing DNS, I want records addressed under
their zone.

#### Acceptance Criteria

1. THE SYSTEM SHALL provide `DomainGroup.list(per_page=, page=)` against
   `/domains`.
2. THE SYSTEM SHALL provide `list_records(domain_name=, per_page=, page=,
   **filters)`, `create_record(domain_name=, body=)`, and
   `delete_record(domain_name=, domain_record_id=)` addressing
   `/domains/{domain_name}/records`.
3. THE SYSTEM SHALL take the zone name as a parameter on every record call
   rather than holding it as group state.

### Requirement 8: Speak the Spaces S3 Surface

**User Story:** As a provisioner staging object storage, I want bucket
operations against Spaces using its own key pair.

#### Acceptance Criteria

1. WHEN `SpacesClient` is constructed THE SYSTEM SHALL build a `SigV4Signer`
   scoped to the `s3` service and to the client's region.
2. THE SYSTEM SHALL derive the endpoint as
   `https://{region}.digitaloceanspaces.com` and SHALL accept an
   `endpoint_url` override for another S3-compatible target or a test double.
3. THE SYSTEM SHALL address buckets PATH-style rather than virtual-host style,
   because a newly created bucket is immediately addressable by path while its
   virtual-host name waits on DNS — so an apply that creates a bucket and then
   heads it would otherwise fail intermittently.
4. THE SYSTEM SHALL implement `head_bucket`, `create_bucket`, `delete_bucket`,
   and `list_buckets`, each taking the capitalised `Bucket` keyword that S3
   call sites already use.
5. THE SYSTEM SHALL sign query parameters along with the method, URL, and
   body.
6. WHEN `delete_bucket` is called against a non-empty bucket THE SYSTEM SHALL
   let `BucketNotEmpty` propagate, because a teardown that silently skipped it
   would report success while leaving billable storage behind.
7. WHEN `list_buckets` decodes a response THE SYSTEM SHALL read bucket `Name`
   elements only and SHALL NOT pick up the owner's display name, returning
   `{"Buckets": []}` when there are none.

### Requirement 9: Report Spaces Failures With the S3 Error Code

**User Story:** As a consumer, I want "bucket absent" distinguishable from
"request broken", because the first is a normal answer and the second must
stop the apply.

#### Acceptance Criteria

1. WHEN a Spaces response status is outside `200..299` THE SYSTEM SHALL raise
   `SpacesRequestError` carrying `status`, `code`, and the raw `body`.
2. THE SYSTEM SHALL read the S3 error code from the first `<Code>` element at
   any depth, matched on its local name, so that a namespaced body decodes the
   same as an un-namespaced one.
3. WHEN the failed response has no body, or a body that does not parse as XML,
   THE SYSTEM SHALL use the HTTP status as the code — so a missing bucket
   reports `"404"` and never an empty string.
4. THE SYSTEM SHALL NOT report an auth or throttle failure with a code a
   caller would read as a missing bucket.

### Requirement 10: Remain Injectable and SDK-Free

**User Story:** As a test author, I want to drive both transports without a
DigitalOcean account.

#### Acceptance Criteria

1. THE SYSTEM SHALL accept a pre-built `session` object on both
   `DigitalOceanRestClient` and `SpacesClient` as the test seam and as the way
   a caller supplies custom transport adapters or proxies.
2. THE SYSTEM SHALL NOT import `pydo`, `boto3`, or `botocore` at any point.
