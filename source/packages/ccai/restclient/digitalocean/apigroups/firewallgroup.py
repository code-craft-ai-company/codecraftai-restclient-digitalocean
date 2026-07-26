"""
    .. module:: firewallgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`FirewallGroup` — the ``/firewalls`` api group.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict

from ccai.restclient.digitalocean.apigroups.collectiongroup import (
    CollectionGroup
)


class FirewallGroup(CollectionGroup):
    """
        The DigitalOcean firewalls collection.
    """

    COLLECTION_PATH = "/firewalls"
    IDENTIFIER_KEYWORD = "firewall_id"

    def update(self, *, firewall_id: Any,
               body: Dict[str, Any]) -> Dict[str, Any]:
        """
            Replace a firewall's configuration.

            The API models this as a PUT, which is a full replacement rather
            than a merge: the body must describe the firewall's complete
            desired state, since omitted rules are removed.

            :param firewall_id: The firewall id.
            :param body: The complete replacement configuration.

            :returns: The decoded response, carrying the firewall under
                ``firewall``.
        """
        rtnval = self._client.request(
            method="PUT",
            path="{}/{}".format(self.COLLECTION_PATH, firewall_id),
            body=body)
        return rtnval

    def delete(self, *, firewall_id: Any) -> Dict[str, Any]:
        """
            Delete a firewall.

            :param firewall_id: The firewall id.

            :returns: The decoded response.
        """
        rtnval = self._delete_by_id(identifier=firewall_id)
        return rtnval
