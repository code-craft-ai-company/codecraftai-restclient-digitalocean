"""
    .. module:: digitaloceanrestclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`DigitalOceanRestClient` — a pure-Python client for the
               DigitalOcean API v2.

    The DigitalOcean API is plain REST over HTTPS with JSON bodies and a
    Bearer token, so this client speaks it directly rather than depending on
    the ``pydo`` SDK.

    The api groups are named to match the surface ``pydo`` presented —
    ``vpcs``, ``firewalls``, ``droplets``, ``volumes``, ``volume_actions``,
    ``ssh_keys``, ``domains`` — and every response is a plain ``dict``,
    because that is how callers already read them.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import json
import os

from typing import Any, Dict, Optional

import requests

from ccai.restclient.digitalocean.digitaloceanapierror import (
    DigitalOceanApiRequestError
)


DIGITALOCEAN_API_BASE = "https://api.digitalocean.com/v2"

DEFAULT_TIMEOUT_SECONDS = 60.0


class DigitalOceanRestClient:
    """
        REST client for the DigitalOcean API v2.

        The api groups are reached through public attributes: ``vpcs``,
        ``firewalls``, ``droplets``, ``volumes``, ``volume_actions``,
        ``ssh_keys``, ``domains``.
    """

    def __init__(self, *, token: str, base_url: str = DIGITALOCEAN_API_BASE,
                 session: Optional[Any] = None,
                 timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """
            Construct a DigitalOceanRestClient.

            :param token: The DigitalOcean personal access token.
            :param base_url: The API base URL.
            :param session: Optional pre-built ``requests.Session`` — the test
                seam and the way a caller supplies custom transport adapters
                or proxies.
            :param timeout_seconds: The default per-request timeout.
        """
        self._token: str = token
        self._base_url: str = base_url.rstrip("/")
        self._timeout_seconds: float = timeout_seconds

        if session is not None:
            self._session = session
        else:
            self._session = requests.Session()

        self._session.headers.update({
            "Authorization": "Bearer {}".format(token),
            "Accept": "application/json",
        })

        from ccai.restclient.digitalocean.apigroups.vpcgroup import VpcGroup
        from ccai.restclient.digitalocean.apigroups.firewallgroup import (
            FirewallGroup
        )
        from ccai.restclient.digitalocean.apigroups.dropletgroup import (
            DropletGroup
        )
        from ccai.restclient.digitalocean.apigroups.volumegroup import (
            VolumeActionGroup, VolumeGroup
        )
        from ccai.restclient.digitalocean.apigroups.sshkeygroup import (
            SshKeyGroup
        )
        from ccai.restclient.digitalocean.apigroups.domaingroup import (
            DomainGroup
        )

        self.vpcs: VpcGroup = VpcGroup(client=self)
        self.firewalls: FirewallGroup = FirewallGroup(client=self)
        self.droplets: DropletGroup = DropletGroup(client=self)
        self.volumes: VolumeGroup = VolumeGroup(client=self)
        self.volume_actions: VolumeActionGroup = VolumeActionGroup(
            client=self)
        self.ssh_keys: SshKeyGroup = SshKeyGroup(client=self)
        self.domains: DomainGroup = DomainGroup(client=self)
        return

    @property
    def base_url(self) -> str:
        """
            Return the API base URL.

            :returns: The base URL.
        """
        rtnval = self._base_url
        return rtnval

    def request(self, *, method: str, path: str,
                params: Optional[Dict[str, Any]] = None,
                body: Optional[Dict[str, Any]] = None,
                timeout_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
            Perform one API request and return the decoded body.

            :param method: The HTTP method.
            :param path: The API path, beginning with ``/``.
            :param params: Optional query parameters; ``None`` values are
                dropped so an unset page size is simply absent.
            :param body: Optional JSON request body.
            :param timeout_seconds: Optional per-request timeout override.

            :returns: The decoded response, or ``{}`` when the response
                carries no body (deletes answer ``204``).

            :raises: :class:`DigitalOceanApiRequestError` on a non-success
                status.
        """
        url = "{}{}".format(self._base_url, path)

        query: Dict[str, Any] = {}
        if params is not None:
            for key, value in params.items():
                if value is not None:
                    query[key] = value

        headers: Dict[str, str] = {}
        payload = None
        if body is not None:
            payload = json.dumps(body)
            headers["Content-Type"] = "application/json"

        timeout = timeout_seconds
        if timeout is None:
            timeout = self._timeout_seconds

        response = self._session.request(method, url, params=query,
                                         data=payload, headers=headers,
                                         timeout=timeout)

        status = getattr(response, "status_code", 0)

        if status < 200 or status >= 300:
            text = getattr(response, "text", "")
            reason = self._extract_error_reason(
                response=response, fallback=getattr(response, "reason", ""))
            err_msg_lines = ["The DigitalOcean API request failed."]
            err_msg_lines.append("METHOD: {}".format(method))
            err_msg_lines.append("PATH: {}".format(path))
            err_msg_lines.append("STATUS: {}".format(status))
            err_msg_lines.append("REASON: {}".format(reason))
            err_msg = os.linesep.join(err_msg_lines)
            raise DigitalOceanApiRequestError(err_msg, status=status,
                                              reason=reason, body=text)

        text = getattr(response, "text", "")
        if text is None or len(text.strip()) == 0:
            rtnval: Dict[str, Any] = {}
            return rtnval

        try:
            decoded = response.json()
        except Exception:
            rtnval = {}
            return rtnval

        if isinstance(decoded, dict) is False:
            rtnval = {"data": decoded}
            return rtnval

        rtnval = decoded
        return rtnval

    def _extract_error_reason(self, *, response: Any,
                              fallback: str) -> str:
        """
            Pull a human-readable reason out of a DigitalOcean error body.

            Failures arrive as ``{"id": ..., "message": ...}``; the message is
            far more useful than the bare HTTP phrase.

            :param response: The failed response.
            :param fallback: The reason to use when the body is unhelpful.

            :returns: The extracted reason.
        """
        try:
            decoded = response.json()
        except Exception:
            rtnval = fallback
            return rtnval

        if isinstance(decoded, dict) is False:
            rtnval = fallback
            return rtnval

        message = decoded.get("message", None)
        if message is None:
            rtnval = fallback
            return rtnval

        identifier = decoded.get("id", None)
        if identifier is not None:
            rtnval = "{}: {}".format(identifier, message)
            return rtnval

        rtnval = str(message)
        return rtnval
