"""
    .. module:: spacesclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`SpacesClient` — a pure-Python client for DigitalOcean
               Spaces, the S3-compatible object store.

    Spaces speaks the S3 API and authenticates with SigV4 using its own
    access-key pair, which is separate from the DigitalOcean API token.  The
    signing itself lives in ``restclient-base`` because AWS and other
    S3-compatible stores need the identical algorithm.

    The method names mirror the S3 surface callers already use
    (``head_bucket(Bucket=...)``) so call sites written against an S3 SDK keep
    their shape, including the capitalised ``Bucket`` keyword.

    Requests are path-style (``https://{region}.digitaloceanspaces.com/
    {bucket}``) rather than virtual-host style.  That is deliberate: a bucket
    created moments ago is immediately addressable by path, while its
    virtual-host name has to wait on DNS — and an apply that creates a bucket
    and then heads it would intermittently fail.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import os
import xml.etree.ElementTree as ElementTree

from typing import Any, Dict, List, Optional

import requests

from ccai.restclient.base.awssigv4 import SigV4Signer

from ccai.restclient.digitalocean.digitaloceanapierror import (
    SpacesRequestError
)


SPACES_HOST_TEMPLATE = "https://{}.digitaloceanspaces.com"

# Spaces presents itself as S3, so the signature is scoped to the s3 service.
SPACES_SERVICE = "s3"

DEFAULT_TIMEOUT_SECONDS = 60.0


def _local_name(tag: str) -> str:
    """
        Strip any XML namespace from an element tag.

        S3 responses are namespaced, and whether a given endpoint declares the
        namespace varies, so matching on the local name is the only reliable
        way to read them.

        :param tag: The element tag.

        :returns: The local name.
    """
    if tag.startswith("{") is True:
        rtnval = tag.split("}", 1)[1]
        return rtnval

    rtnval = tag
    return rtnval


def _iter_local(element: Any, name: str) -> List[Any]:
    """
        Find descendant elements whose local name matches, at any depth.

        :param element: The element to search under.
        :param name: The local name to match.

        :returns: The matching elements.
    """
    rtnval = [found for found in element.iter()
              if _local_name(found.tag) == name]
    return rtnval


class SpacesClient:
    """
        S3-compatible client for one DigitalOcean Spaces region.

        Only bucket-level operations are implemented, which is what the
        provisioning venue needs; object operations can be added against the
        same signed transport when something needs them.
    """

    def __init__(self, *, access_key: str, secret_key: str, region: str,
                 endpoint_url: Optional[str] = None,
                 session: Optional[Any] = None,
                 timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """
            Construct a SpacesClient.

            :param access_key: The Spaces access key.
            :param secret_key: The Spaces secret key.
            :param region: The Spaces region slug, e.g. ``nyc3``.  It is both
                the host prefix and the SigV4 region.
            :param endpoint_url: Optional endpoint override, for a
                non-DigitalOcean S3-compatible target or a test double.
            :param session: Optional pre-built ``requests.Session`` — the test
                seam.
            :param timeout_seconds: The default per-request timeout.
        """
        self._region: str = region

        if endpoint_url is not None:
            self._endpoint: str = endpoint_url.rstrip("/")
        else:
            self._endpoint = SPACES_HOST_TEMPLATE.format(region)

        self._timeout_seconds: float = timeout_seconds

        self._signer = SigV4Signer(access_key=access_key,
                                   secret_key=secret_key, region=region,
                                   service=SPACES_SERVICE)

        if session is not None:
            self._session = session
        else:
            self._session = requests.Session()
        return

    @property
    def region(self) -> str:
        """
            Return the region this client is scoped to.

            :returns: The region slug.
        """
        rtnval = self._region
        return rtnval

    @property
    def endpoint_url(self) -> str:
        """
            Return the endpoint this client addresses.

            :returns: The endpoint URL.
        """
        rtnval = self._endpoint
        return rtnval

    def _request(self, *, method: str, path: str,
                 params: Optional[Dict[str, Any]] = None,
                 body: Optional[bytes] = None) -> Any:
        """
            Perform one signed request against the Spaces endpoint.

            :param method: The HTTP method.
            :param path: The request path, beginning with ``/``.
            :param params: Optional query parameters, which are signed.
            :param body: Optional request body.

            :returns: The response object.

            :raises: :class:`SpacesRequestError` on a non-success status.
        """
        url = "{}{}".format(self._endpoint, path)

        headers = self._signer.sign(method=method, url=url, params=params,
                                    body=body)

        response = self._session.request(method, url, params=params or {},
                                         data=body, headers=headers,
                                         timeout=self._timeout_seconds)

        status = getattr(response, "status_code", 0)

        if status < 200 or status >= 300:
            text = getattr(response, "text", "")
            code = self._extract_error_code(response=response, status=status)
            err_msg_lines = ["The DigitalOcean Spaces request failed."]
            err_msg_lines.append("METHOD: {}".format(method))
            err_msg_lines.append("PATH: {}".format(path))
            err_msg_lines.append("STATUS: {}".format(status))
            err_msg_lines.append("CODE: {}".format(code))
            err_msg = os.linesep.join(err_msg_lines)
            raise SpacesRequestError(err_msg, status=status, code=code,
                                     body=text)

        rtnval = response
        return rtnval

    def _extract_error_code(self, *, response: Any, status: int) -> str:
        """
            Pull the S3 error code out of a failed response.

            S3 reports failures as an XML ``<Error><Code>`` document, but a
            failed HEAD has no body at all — so the status is used as the code
            in that case.  Callers distinguish "bucket absent" from "request
            broken" on this value, so it must never come back empty for a 404.

            :param response: The failed response.
            :param status: The HTTP status code.

            :returns: The S3 error code, or the status as a string.
        """
        text = getattr(response, "text", "")

        if text is not None and len(text.strip()) > 0:
            try:
                root = ElementTree.fromstring(text)
            except ElementTree.ParseError:
                root = None

            if root is not None:
                for found in _iter_local(root, "Code"):
                    if found.text is None:
                        continue
                    rtnval = found.text.strip()
                    return rtnval

        rtnval = str(status)
        return rtnval

    def head_bucket(self, *, Bucket: str) -> Dict[str, Any]:
        """
            Check that a bucket exists and is reachable.

            :param Bucket: The bucket name.  Capitalised to match the S3
                surface callers already use.

            :returns: A dict carrying the response status.

            :raises: :class:`SpacesRequestError` — with ``code`` ``"404"`` when
                the bucket does not exist, which the caller recovers, and any
                other code for auth or throttle failures, which it must not.
        """
        response = self._request(method="HEAD",
                                 path="/{}".format(Bucket))

        rtnval = {"ResponseMetadata": {
            "HTTPStatusCode": getattr(response, "status_code", 200)}}
        return rtnval

    def create_bucket(self, *, Bucket: str) -> Dict[str, Any]:
        """
            Create a bucket in this client's region.

            :param Bucket: The bucket name.

            :returns: A dict carrying the bucket location.
        """
        response = self._request(method="PUT", path="/{}".format(Bucket))

        rtnval = {"Location": "/{}".format(Bucket),
                  "ResponseMetadata": {
                      "HTTPStatusCode": getattr(response, "status_code",
                                                200)}}
        return rtnval

    def delete_bucket(self, *, Bucket: str) -> Dict[str, Any]:
        """
            Delete a bucket.

            The API refuses to delete a bucket that still holds objects,
            surfacing as ``BucketNotEmpty``.  That is left to propagate: a
            teardown that silently skipped a non-empty bucket would report
            success while leaving billable storage behind.

            :param Bucket: The bucket name.

            :returns: A dict carrying the response status.
        """
        response = self._request(method="DELETE", path="/{}".format(Bucket))

        rtnval = {"ResponseMetadata": {
            "HTTPStatusCode": getattr(response, "status_code", 204)}}
        return rtnval

    def list_buckets(self) -> Dict[str, Any]:
        """
            List every bucket the credential can see.

            :returns: A dict carrying ``Buckets``, a list of ``{"Name": ...}``
                entries, matching the S3 response shape.
        """
        response = self._request(method="GET", path="/")

        names: List[Dict[str, Any]] = []

        text = getattr(response, "text", "")
        if text is not None and len(text.strip()) > 0:
            try:
                root = ElementTree.fromstring(text)
            except ElementTree.ParseError:
                root = None

            if root is not None:
                for bucket in _iter_local(root, "Bucket"):
                    for name in _iter_local(bucket, "Name"):
                        if name.text is None:
                            continue
                        names.append({"Name": name.text.strip()})
                        break

        rtnval = {"Buckets": names}
        return rtnval
