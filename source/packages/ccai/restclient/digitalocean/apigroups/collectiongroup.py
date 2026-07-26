"""
    .. module:: collectiongroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`CollectionGroup` — the shared behaviour of the regular
               DigitalOcean collections.

    Most DigitalOcean collections follow the same shape: a collection path
    (``/vpcs``), entries nested under the plural name (``vpcs``) on a list,
    the resource nested under the singular name (``vpc``) on a create, and
    deletion by id.  That uniformity lives here.

    The method names and keyword names deliberately match the ones the ``pydo``
    SDK used — ``list(per_page=, page=)``, ``create(body=)``,
    ``delete(vpc_id=)`` — so call sites written against the SDK keep their
    shape.  Where a caller's keyword differed from pydo's own, the CALLER's
    spelling wins, because this client is what defines the contract now.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, Optional


class CollectionGroup:
    """
        Shared behaviour for a regular DigitalOcean collection.

        :cvar COLLECTION_PATH: The collection path, e.g. ``/vpcs``.
        :cvar IDENTIFIER_KEYWORD: The keyword callers name the resource by,
            e.g. ``vpc_id``.
    """

    COLLECTION_PATH: str = ""
    IDENTIFIER_KEYWORD: str = ""

    def __init__(self, *, client: Any) -> None:
        """
            Construct a collection group bound to a client.

            :param client: The owning :class:`DigitalOceanRestClient`.
        """
        self._client = client
        return

    def list(self, *, per_page: Optional[int] = None,
             page: Optional[int] = None,
             **filters: Any) -> Dict[str, Any]:
        """
            List one page of the collection.

            This returns ONE page, exactly as the SDK did.  Callers that need
            the whole collection follow ``links.pages.next`` themselves — the
            venue has a helper for it — so paging stays where the caller can
            see it.

            :param per_page: Optional page size.
            :param page: Optional page number.
            :param filters: Any further query parameters, e.g. ``tag_name``.

            :returns: The decoded response, carrying the entries under the
                collection's plural key plus ``links`` and ``meta``.
        """
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        for key, value in filters.items():
            params[key] = value

        rtnval = self._client.request(method="GET",
                                     path=self.COLLECTION_PATH,
                                     params=params)
        return rtnval

    def create(self, *, body: Dict[str, Any]) -> Dict[str, Any]:
        """
            Create a resource.

            :param body: The creation body, passed through as given.

            :returns: The decoded response, carrying the resource under the
                collection's singular key.
        """
        rtnval = self._client.request(method="POST",
                                     path=self.COLLECTION_PATH, body=body)
        return rtnval

    def _delete_by_id(self, *, identifier: Any) -> Dict[str, Any]:
        """
            Delete a resource by id.

            :param identifier: The resource id.

            :returns: The decoded response, empty on a ``204``.
        """
        rtnval = self._client.request(
            method="DELETE",
            path="{}/{}".format(self.COLLECTION_PATH, identifier))
        return rtnval
