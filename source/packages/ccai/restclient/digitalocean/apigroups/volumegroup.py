"""
    .. module:: volumegroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`VolumeGroup` and :class:`VolumeActionGroup` — the
               ``/volumes`` api group and its actions sub-collection.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict

from ccai.restclient.digitalocean.apigroups.collectiongroup import (
    CollectionGroup
)


class VolumeGroup(CollectionGroup):
    """
        The DigitalOcean block-storage volumes collection.
    """

    COLLECTION_PATH = "/volumes"
    IDENTIFIER_KEYWORD = "volume_id"

    def delete(self, *, volume_id: Any) -> Dict[str, Any]:
        """
            Delete a volume.

            :param volume_id: The volume id.

            :returns: The decoded response.
        """
        rtnval = self._delete_by_id(identifier=volume_id)
        return rtnval


class VolumeActionGroup:
    """
        The volume actions sub-collection.

        Attach and detach are modelled by the API as actions posted against a
        volume, with the verb named inside the body rather than by the path.
    """

    def __init__(self, *, client: Any) -> None:
        """
            Construct a volume-action group bound to a client.

            :param client: The owning :class:`DigitalOceanRestClient`.
        """
        self._client = client
        return

    def post_by_id(self, *, volume_id: Any,
                   body: Dict[str, Any]) -> Dict[str, Any]:
        """
            Post an action against one volume.

            :param volume_id: The volume id.
            :param body: The action body, carrying ``type`` and whatever that
                action needs (e.g. ``droplet_id``, ``region``).

            :returns: The decoded response, carrying the action record under
                ``action``.
        """
        rtnval = self._client.request(
            method="POST",
            path="/volumes/{}/actions".format(volume_id), body=body)
        return rtnval
