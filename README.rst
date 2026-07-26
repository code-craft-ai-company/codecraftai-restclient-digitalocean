==================================
codecraftai-restclient-digitalocean
==================================

A pure-Python client for the `DigitalOcean API v2
<https://docs.digitalocean.com/reference/api/>`_ and for Spaces, its
S3-compatible object store.

Two clients live here because DigitalOcean has two authentication systems: the
API is a Bearer personal access token, while Spaces has its own S3-style
access-key pair and SigV4 signing.  A token carries no authority in Spaces and
a Spaces key carries none in the API.

The API client
==============

The api groups are named to match the surface the ``pydo`` SDK presented, and
every response is a plain ``dict``:

.. code-block:: python

    from ccai.restclient.digitalocean.digitaloceanrestclient import (
        DigitalOceanRestClient
    )

    client = DigitalOceanRestClient(token=token)

    created = client.droplets.create(body={"name": "srv-a", ...})
    droplet = created.get("droplet", {})

    page = client.droplets.list(per_page=200, page=1, tag_name="run:abc")
    for entry in page.get("droplets", []):
        ...

    client.droplets.destroy(droplet_id=droplet["id"])

Groups: ``vpcs``, ``firewalls``, ``droplets``, ``volumes``,
``volume_actions``, ``ssh_keys``, ``domains``.

``list`` returns ONE page, exactly as the SDK did, so paging stays visible to
the caller rather than hidden in the transport.  Follow ``links.pages.next``
to exhaust a collection.

The Spaces client
=================

.. code-block:: python

    from ccai.restclient.digitalocean.spacesclient import SpacesClient

    spaces = SpacesClient(access_key=key, secret_key=secret, region="nyc3")

    spaces.create_bucket(Bucket="my-bucket")
    spaces.head_bucket(Bucket="my-bucket")
    spaces.delete_bucket(Bucket="my-bucket")

The method and keyword names mirror the S3 surface — including the capitalised
``Bucket`` — so call sites written against an S3 SDK keep their shape.
Signing comes from :mod:`ccai.restclient.base.awssigv4`, shared with AWS and
any other S3-compatible store.

Design notes
============

**Requests are path-style.** A bucket created moments ago is immediately
addressable at ``https://{region}.digitaloceanspaces.com/{bucket}``, while its
virtual-host name has to wait on DNS.  An apply that creates a bucket and then
heads it would intermittently fail under virtual-host addressing.

**Spaces errors carry the S3 code as an attribute.**
:class:`SpacesRequestError` exposes ``status``, ``code`` and ``body``.  Callers
distinguish "bucket absent" (recover) from "auth or throttle failed" (do not
recover) on that code, so it is first-class rather than something to dig out of
a message.  A failed ``HEAD`` has no body at all, so the status is used as the
code in that case — it must never come back empty for a 404.

**Error XML is matched on local names.** S3 responses are namespaced, and
whether an endpoint declares the namespace varies, so tags are matched with the
namespace stripped.

**Errors are thin.** Translating status codes into a typed hierarchy is the
consumer's policy, not the transport's.
