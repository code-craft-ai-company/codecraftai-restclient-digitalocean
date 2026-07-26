"""
    .. module:: vpcgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`VpcGroup` — the ``/vpcs`` api group.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict

from ccai.restclient.digitalocean.apigroups.collectiongroup import (
    CollectionGroup
)


class VpcGroup(CollectionGroup):
    """
        The DigitalOcean VPCs collection.
    """

    COLLECTION_PATH = "/vpcs"
    IDENTIFIER_KEYWORD = "vpc_id"

    def delete(self, *, vpc_id: Any) -> Dict[str, Any]:
        """
            Delete a VPC.

            :param vpc_id: The VPC id.

            :returns: The decoded response.
        """
        rtnval = self._delete_by_id(identifier=vpc_id)
        return rtnval
