"""
    .. module:: sshkeygroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`SshKeyGroup` — the account ssh-keys api group.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict

from ccai.restclient.digitalocean.apigroups.collectiongroup import (
    CollectionGroup
)


class SshKeyGroup(CollectionGroup):
    """
        The DigitalOcean ssh-keys collection.

        The path is ``/account/keys`` — ssh keys belong to the account rather
        than to any one resource — while the response key is ``ssh_keys``.
        That mismatch is the API's, not a mistake here.
    """

    COLLECTION_PATH = "/account/keys"
    IDENTIFIER_KEYWORD = "ssh_key_id"

    def delete(self, *, ssh_key_id: Any) -> Dict[str, Any]:
        """
            Delete an ssh key.

            The API accepts either the numeric id or the key fingerprint in
            this position, so both work.

            :param ssh_key_id: The ssh key id or fingerprint.

            :returns: The decoded response.
        """
        rtnval = self._delete_by_id(identifier=ssh_key_id)
        return rtnval
