"""
    .. module:: dropletgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`DropletGroup` — the ``/droplets`` api group.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict

from ccai.restclient.digitalocean.apigroups.collectiongroup import (
    CollectionGroup
)


class DropletGroup(CollectionGroup):
    """
        The DigitalOcean droplets collection.
    """

    COLLECTION_PATH = "/droplets"
    IDENTIFIER_KEYWORD = "droplet_id"

    def destroy(self, *, droplet_id: Any) -> Dict[str, Any]:
        """
            Destroy a droplet.

            Named ``destroy`` rather than ``delete`` to match the surface
            callers already use for this collection.

            :param droplet_id: The droplet id.

            :returns: The decoded response.
        """
        rtnval = self._delete_by_id(identifier=droplet_id)
        return rtnval
