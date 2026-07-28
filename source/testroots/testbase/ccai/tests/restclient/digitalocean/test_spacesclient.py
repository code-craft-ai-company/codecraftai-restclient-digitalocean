"""
    .. module:: test_spacesclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Tests for the DigitalOcean Spaces (S3-compatible) client.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from ccai import testbase

from ccai.restclient.digitalocean.digitaloceanapierror import (
    SpacesRequestError
)
from ccai.restclient.digitalocean.spacesclient import SpacesClient

from ccai.tests.restclient.digitalocean.fakesession import (
    FakeResponse, FakeSession
)


NO_SUCH_BUCKET_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    "<Error><Code>NoSuchBucket</Code>"
    "<Message>The specified bucket does not exist</Message></Error>"
)

NAMESPACED_ERROR_XML = (
    '<Error xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
    "<Code>BucketNotEmpty</Code><Message>not empty</Message></Error>"
)

LIST_BUCKETS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<ListAllMyBucketsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
    "<Owner><ID>abc</ID><DisplayName>owner-display</DisplayName></Owner>"
    "<Buckets>"
    "<Bucket><Name>bucket-one</Name>"
    "<CreationDate>2026-01-01T00:00:00.000Z</CreationDate></Bucket>"
    "<Bucket><Name>bucket-two</Name>"
    "<CreationDate>2026-01-02T00:00:00.000Z</CreationDate></Bucket>"
    "</Buckets></ListAllMyBucketsResult>"
)


def _build_client(**overrides):
    """
        Build a Spaces client over a fake session.

        :returns: A ``(client, session)`` pair.
    """
    session = FakeSession()
    kwargs = {"access_key": "DO00EXAMPLE", "secret_key": "secret",
              "region": "nyc3", "session": session}
    kwargs.update(overrides)
    client = SpacesClient(**kwargs)
    return client, session


# ----------------------------------------------------------------------
# construction and addressing
# ----------------------------------------------------------------------

def test_endpoint_is_derived_from_the_region():
    client, session = _build_client()

    assert client.region == "nyc3"
    assert client.endpoint_url == "https://nyc3.digitaloceanspaces.com"
    return


def test_endpoint_can_be_overridden():
    client, session = _build_client(endpoint_url="https://minio.local/")

    assert client.endpoint_url == "https://minio.local"
    return


def test_requests_are_path_style():
    client, session = _build_client()

    client.head_bucket(Bucket="my-bucket")

    # Path-style, not virtual-host: a bucket created moments ago is
    # addressable by path immediately, while its DNS name is not.
    assert session.calls[0]["url"] == \
        "https://nyc3.digitaloceanspaces.com/my-bucket"
    return


# ----------------------------------------------------------------------
# signing
# ----------------------------------------------------------------------

def test_requests_are_sigv4_signed():
    client, session = _build_client()

    client.head_bucket(Bucket="my-bucket")

    headers = session.calls[0]["headers"]
    authorization = headers["Authorization"]
    assert authorization.startswith("AWS4-HMAC-SHA256 ")
    assert "Credential=DO00EXAMPLE/" in authorization
    # The signature is scoped to the s3 service and this region.
    assert "/nyc3/s3/aws4_request" in authorization
    return


def test_signed_headers_are_actually_sent():
    client, session = _build_client()

    client.head_bucket(Bucket="my-bucket")

    headers = session.calls[0]["headers"]
    # Sending a different header set than was signed fails, so the headers the
    # signer added must reach the transport.
    assert headers["host"] == "nyc3.digitaloceanspaces.com"
    assert "x-amz-date" in headers
    assert "x-amz-content-sha256" in headers
    return


def test_each_bucket_gets_a_distinct_signature():
    client, session = _build_client()

    client.head_bucket(Bucket="bucket-one")
    client.head_bucket(Bucket="bucket-two")

    first = session.calls[0]["headers"]["Authorization"]
    second = session.calls[1]["headers"]["Authorization"]
    # The canonical URI is part of the signature.
    assert first != second
    return


# ----------------------------------------------------------------------
# bucket operations
# ----------------------------------------------------------------------

def test_head_bucket_succeeds_for_an_existing_bucket():
    client, session = _build_client()
    session.queue(method="HEAD", path="/my-bucket",
                  response=FakeResponse(status_code=200, text=""))

    result = client.head_bucket(Bucket="my-bucket")

    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200
    return


def test_create_bucket_is_a_put():
    client, session = _build_client()
    session.queue(method="PUT", path="/my-bucket",
                  response=FakeResponse(status_code=200, text=""))

    result = client.create_bucket(Bucket="my-bucket")

    assert session.calls[0]["method"] == "PUT"
    assert result["Location"] == "/my-bucket"
    return


def test_delete_bucket_is_a_delete():
    client, session = _build_client()
    session.queue(method="DELETE", path="/my-bucket",
                  response=FakeResponse(status_code=204, text=""))

    result = client.delete_bucket(Bucket="my-bucket")

    assert session.calls[0]["method"] == "DELETE"
    assert result["ResponseMetadata"]["HTTPStatusCode"] == 204
    return


# ----------------------------------------------------------------------
# error codes
# ----------------------------------------------------------------------

def test_missing_bucket_reports_the_s3_error_code():
    client, session = _build_client()
    session.queue(method="GET", path="/my-bucket",
                  response=FakeResponse(status_code=404, reason="Not Found",
                                        text=NO_SUCH_BUCKET_XML))

    with testbase.raises(SpacesRequestError) as caught:
        client._request(method="GET", path="/my-bucket")

    assert caught.value.status == 404
    assert caught.value.code == "NoSuchBucket"
    return


def test_error_code_is_read_through_the_xml_namespace():
    client, session = _build_client()
    session.queue(method="DELETE", path="/my-bucket",
                  response=FakeResponse(status_code=409, reason="Conflict",
                                        text=NAMESPACED_ERROR_XML))

    with testbase.raises(SpacesRequestError) as caught:
        client.delete_bucket(Bucket="my-bucket")

    # S3 responses are namespaced and whether an endpoint declares the
    # namespace varies, so tags are matched on local name.
    assert caught.value.code == "BucketNotEmpty"
    return


def test_bodiless_failure_falls_back_to_the_status_as_code():
    client, session = _build_client()
    session.queue(method="HEAD", path="/my-bucket",
                  response=FakeResponse(status_code=404, reason="Not Found",
                                        text=""))

    with testbase.raises(SpacesRequestError) as caught:
        client.head_bucket(Bucket="my-bucket")

    # A failed HEAD carries no body, and callers decide "absent vs broken" on
    # the code — so it must never be empty for a 404.
    assert caught.value.code == "404"
    assert caught.value.status == 404
    return


def test_unparseable_body_falls_back_to_the_status_as_code():
    client, session = _build_client()
    session.queue(method="HEAD", path="/my-bucket",
                  response=FakeResponse(status_code=403, reason="Forbidden",
                                        text="not xml at all <<<"))

    with testbase.raises(SpacesRequestError) as caught:
        client.head_bucket(Bucket="my-bucket")

    assert caught.value.code == "403"
    return


def test_auth_failure_is_not_reported_as_a_missing_bucket():
    client, session = _build_client()
    session.queue(method="HEAD", path="/my-bucket",
                  response=FakeResponse(status_code=403, reason="Forbidden",
                                        text=""))

    with testbase.raises(SpacesRequestError) as caught:
        client.head_bucket(Bucket="my-bucket")

    # Masking an auth failure as "does not exist" would make an apply try to
    # create a bucket it cannot see, every time.
    assert caught.value.code != "404"
    assert caught.value.code != "NoSuchBucket"
    return


# ----------------------------------------------------------------------
# listing
# ----------------------------------------------------------------------

def test_list_buckets_reads_bucket_names():
    client, session = _build_client()
    session.queue(method="GET", path="/",
                  response=FakeResponse(status_code=200,
                                        text=LIST_BUCKETS_XML))

    result = client.list_buckets()

    names = [entry["Name"] for entry in result["Buckets"]]
    assert names == ["bucket-one", "bucket-two"]
    return


def test_list_buckets_does_not_mistake_the_owner_display_name():
    client, session = _build_client()
    session.queue(method="GET", path="/",
                  response=FakeResponse(status_code=200,
                                        text=LIST_BUCKETS_XML))

    result = client.list_buckets()

    # DisplayName also ends in "Name"; scoping to Bucket elements is what
    # keeps the owner out of the bucket list.
    names = [entry["Name"] for entry in result["Buckets"]]
    assert "owner-display" not in names
    return


def test_list_buckets_is_empty_when_there_are_none():
    client, session = _build_client()
    session.queue(method="GET", path="/",
                  response=FakeResponse(status_code=200, text=""))

    assert client.list_buckets() == {"Buckets": []}
    return
