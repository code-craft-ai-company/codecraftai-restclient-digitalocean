"""
    .. module:: digitaloceanapierror
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Errors raised for non-success DigitalOcean responses.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Optional


class DigitalOceanApiRequestError(Exception):
    """
        Raised when the DigitalOcean API returns a non-success status.

        :ivar status: The HTTP status code.
        :ivar reason: The message from the API's error body, or the HTTP
            reason phrase.
        :ivar body: The raw response body text.
    """

    def __init__(self, message: str, *, status: int = 0,
                 reason: str = "", body: Optional[str] = None) -> None:
        """
            Construct a DigitalOceanApiRequestError.

            :param message: The human-readable error message.
            :param status: The HTTP status code.
            :param reason: The extracted reason.
            :param body: The raw response body.
        """
        super().__init__(message)
        self.status: int = status
        self.reason: str = reason
        self.body: Optional[str] = body
        return


class SpacesRequestError(Exception):
    """
        Raised when a Spaces (S3-compatible) request returns a non-success
        status.

        The ``code`` carries the S3 error code parsed out of the XML body
        (``NoSuchBucket``, ``BucketAlreadyOwnedByYou`` ...).  Callers
        distinguish "absent" from "broken" on that code, so it is a first-class
        attribute rather than something to dig out of a message: a missing
        bucket is a normal answer, while an auth or throttle failure must never
        be mistaken for one.

        :ivar status: The HTTP status code.
        :ivar code: The S3 error code, empty when the body carried none.
        :ivar body: The raw response body text.
    """

    def __init__(self, message: str, *, status: int = 0, code: str = "",
                 body: Optional[str] = None) -> None:
        """
            Construct a SpacesRequestError.

            :param message: The human-readable error message.
            :param status: The HTTP status code.
            :param code: The S3 error code.
            :param body: The raw response body.
        """
        super().__init__(message)
        self.status: int = status
        self.code: str = code
        self.body: Optional[str] = body
        return
