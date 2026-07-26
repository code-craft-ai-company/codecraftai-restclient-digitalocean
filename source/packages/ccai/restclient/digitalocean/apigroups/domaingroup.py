"""
    .. module:: domaingroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`DomainGroup` — the ``/domains`` api group and its
               records sub-collection.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, Optional


class DomainGroup:
    """
        The DigitalOcean domains collection and its DNS records.

        Records are addressed under their zone (``/domains/{name}/records``),
        so the zone name is a parameter on every record call rather than
        state held by the group.
    """

    COLLECTION_PATH = "/domains"

    def __init__(self, *, client: Any) -> None:
        """
            Construct a domain group bound to a client.

            :param client: The owning :class:`DigitalOceanRestClient`.
        """
        self._client = client
        return

    def list(self, *, per_page: Optional[int] = None,
             page: Optional[int] = None) -> Dict[str, Any]:
        """
            List one page of the account's domains.

            :param per_page: Optional page size.
            :param page: Optional page number.

            :returns: The decoded response, carrying ``domains``.
        """
        rtnval = self._client.request(
            method="GET", path=self.COLLECTION_PATH,
            params={"per_page": per_page, "page": page})
        return rtnval

    def list_records(self, *, domain_name: str,
                     per_page: Optional[int] = None,
                     page: Optional[int] = None,
                     **filters: Any) -> Dict[str, Any]:
        """
            List one page of a zone's DNS records.

            :param domain_name: The zone name.
            :param per_page: Optional page size.
            :param page: Optional page number.
            :param filters: Any further query parameters, e.g. ``name`` or
                ``type``.

            :returns: The decoded response, carrying ``domain_records``.
        """
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        for key, value in filters.items():
            params[key] = value

        rtnval = self._client.request(
            method="GET",
            path="{}/{}/records".format(self.COLLECTION_PATH, domain_name),
            params=params)
        return rtnval

    def create_record(self, *, domain_name: str,
                      body: Dict[str, Any]) -> Dict[str, Any]:
        """
            Create a DNS record in a zone.

            :param domain_name: The zone name.
            :param body: The record body, carrying ``type``, ``name``,
                ``data`` and optionally ``ttl``.

            :returns: The decoded response, carrying ``domain_record``.
        """
        rtnval = self._client.request(
            method="POST",
            path="{}/{}/records".format(self.COLLECTION_PATH, domain_name),
            body=body)
        return rtnval

    def delete_record(self, *, domain_name: str,
                      domain_record_id: Any) -> Dict[str, Any]:
        """
            Delete a DNS record from a zone.

            :param domain_name: The zone name.
            :param domain_record_id: The record id.

            :returns: The decoded response.
        """
        rtnval = self._client.request(
            method="DELETE",
            path="{}/{}/records/{}".format(self.COLLECTION_PATH, domain_name,
                                           domain_record_id))
        return rtnval
