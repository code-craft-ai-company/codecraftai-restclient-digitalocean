"""
    .. module:: fakesession
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: A recording fake ``requests.Session`` for the DigitalOcean
               client tests.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import json

from typing import Any, Dict, List, Optional


class FakeResponse:
    """
        Minimal stand-in for a ``requests.Response``.
    """

    def __init__(self, *, status_code: int = 200,
                 payload: Optional[Any] = None, text: Optional[str] = None,
                 reason: str = "OK") -> None:
        self.status_code = status_code
        self.reason = reason
        if text is not None:
            self.text = text
        elif payload is not None:
            self.text = json.dumps(payload)
        else:
            self.text = ""
        self._payload = payload

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


class FakeSession:
    """
        Records requests and replays queued responses.
    """

    def __init__(self) -> None:
        self.headers: Dict[str, str] = {}
        self.calls: List[Dict[str, Any]] = []
        self.responses: Dict[str, List[FakeResponse]] = {}
        self.default_response = FakeResponse(payload={})

    def queue(self, *, method: str, path: str,
              response: FakeResponse) -> None:
        """
            Queue a response for a method/path pair.

            :param method: The HTTP method.
            :param path: The path (suffix match).
            :param response: The response to return.
        """
        key = "{} {}".format(method.upper(), path)
        self.responses.setdefault(key, []).append(response)
        return

    def request(self, method: str, url: str, params=None, data=None,
                headers=None, timeout=None) -> FakeResponse:
        """
            Record and answer a request.
        """
        body = None
        if data is not None:
            if isinstance(data, bytes) is True:
                body = data
            else:
                body = json.loads(data)

        self.calls.append({"method": method, "url": url,
                           "params": params or {}, "body": body,
                           "headers": headers or {}, "timeout": timeout})

        for key, queued in self.responses.items():
            wanted_method, _, wanted_path = key.partition(" ")
            if method.upper() == wanted_method and url.endswith(wanted_path):
                if len(queued) > 0:
                    rtnval = queued.pop(0)
                    return rtnval

        rtnval = self.default_response
        return rtnval
