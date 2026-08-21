"""
    .. module:: test_digitaloceanrestclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Tests for the DigitalOcean API v2 client.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from ccai import testbase

from ccai.restclient.digitalocean.digitaloceanapierror import (
    DigitalOceanApiRequestError
)
from ccai.restclient.digitalocean.digitaloceanrestclient import (
    DigitalOceanRestClient
)

from .fakesession import (
    FakeResponse, FakeSession
)


def _build_client():
    """
        Build a client over a fake session.

        :returns: A ``(client, session)`` pair.
    """
    session = FakeSession()
    client = DigitalOceanRestClient(token="dop_v1_test", session=session)
    return client, session


# ----------------------------------------------------------------------
# transport
# ----------------------------------------------------------------------

def test_client_sends_bearer_token():
    client, session = _build_client()

    assert session.headers["Authorization"] == "Bearer dop_v1_test"
    assert session.headers["Accept"] == "application/json"
    return


def test_request_drops_none_query_parameters():
    client, session = _build_client()

    client.vpcs.list()

    # An unset page size must be absent rather than sent as null.
    assert session.calls[0]["params"] == {}
    return


def test_list_forwards_paging_and_filters():
    client, session = _build_client()

    client.droplets.list(per_page=200, page=2, tag_name="run:abc")

    params = session.calls[0]["params"]
    assert params == {"per_page": 200, "page": 2, "tag_name": "run:abc"}
    return


def test_delete_tolerates_a_bodiless_response():
    client, session = _build_client()
    session.queue(method="DELETE", path="/vpcs/v1",
                  response=FakeResponse(status_code=204, text=""))

    assert client.vpcs.delete(vpc_id="v1") == {}
    return


def test_error_reason_comes_from_the_message_field():
    client, session = _build_client()
    session.queue(method="GET", path="/vpcs",
                  response=FakeResponse(
                      status_code=422, reason="Unprocessable",
                      payload={"id": "unprocessable_entity",
                               "message": "name already exists"}))

    with testbase.raises(DigitalOceanApiRequestError) as caught:
        client.vpcs.list()

    assert caught.value.status == 422
    assert caught.value.reason == "unprocessable_entity: name already exists"
    return


def test_error_falls_back_to_the_http_reason():
    client, session = _build_client()
    session.queue(method="GET", path="/vpcs",
                  response=FakeResponse(status_code=500,
                                        reason="Server Error", text="boom"))

    with testbase.raises(DigitalOceanApiRequestError) as caught:
        client.vpcs.list()

    assert caught.value.reason == "Server Error"
    assert caught.value.body == "boom"
    return


# ----------------------------------------------------------------------
# collection paths
# ----------------------------------------------------------------------

@testbase.parametrize("group_name,path", [
    ("vpcs", "/vpcs"),
    ("firewalls", "/firewalls"),
    ("droplets", "/droplets"),
    ("volumes", "/volumes"),
    ("ssh_keys", "/account/keys"),
])
def test_collections_address_their_own_path(group_name, path):
    client, session = _build_client()

    getattr(client, group_name).list()

    assert session.calls[0]["url"].endswith(path)
    return


def test_ssh_keys_live_under_account_keys():
    client, session = _build_client()
    session.queue(method="GET", path="/account/keys",
                  response=FakeResponse(
                      payload={"ssh_keys": [{"id": 1, "name": "k"}]}))

    page = client.ssh_keys.list()

    # The path is /account/keys but the response key is ssh_keys; that
    # mismatch is the API's.
    assert [entry["id"] for entry in page["ssh_keys"]] == [1]
    return


# ----------------------------------------------------------------------
# creates
# ----------------------------------------------------------------------

@testbase.parametrize("group_name,singular", [
    ("vpcs", "vpc"),
    ("firewalls", "firewall"),
    ("droplets", "droplet"),
    ("volumes", "volume"),
    ("ssh_keys", "ssh_key"),
])
def test_create_returns_the_resource_under_its_singular_key(group_name,
                                                            singular):
    client, session = _build_client()
    group = getattr(client, group_name)
    session.queue(method="POST", path=group.COLLECTION_PATH,
                  response=FakeResponse(status_code=201,
                                        payload={singular: {"id": "x1"}}))

    created = group.create(body={"name": "thing"})

    assert created.get(singular, {}).get("id") == "x1"
    assert session.calls[0]["body"] == {"name": "thing"}
    return


def test_create_passes_the_body_through_unchanged():
    client, session = _build_client()
    body = {"name": "srv-a", "region": "nyc3", "size": "s-1vcpu-1gb",
            "tags": ["run:abc"], "user_data": "#cloud-config"}

    client.droplets.create(body=body)

    assert session.calls[0]["body"] == body
    return


# ----------------------------------------------------------------------
# deletes
# ----------------------------------------------------------------------

def test_vpc_delete_addresses_the_item_path():
    client, session = _build_client()

    client.vpcs.delete(vpc_id="v1")

    assert session.calls[0]["method"] == "DELETE"
    assert session.calls[0]["url"].endswith("/vpcs/v1")
    return


def test_droplet_uses_destroy_not_delete():
    client, session = _build_client()

    client.droplets.destroy(droplet_id=42)

    assert session.calls[0]["method"] == "DELETE"
    assert session.calls[0]["url"].endswith("/droplets/42")
    return


def test_volume_delete_addresses_the_item_path():
    client, session = _build_client()

    client.volumes.delete(volume_id="vol-1")

    assert session.calls[0]["url"].endswith("/volumes/vol-1")
    return


def test_ssh_key_delete_accepts_id_or_fingerprint():
    client, session = _build_client()

    client.ssh_keys.delete(ssh_key_id=7)
    client.ssh_keys.delete(ssh_key_id="aa:bb:cc")

    assert session.calls[0]["url"].endswith("/account/keys/7")
    assert session.calls[1]["url"].endswith("/account/keys/aa:bb:cc")
    return


# ----------------------------------------------------------------------
# firewalls
# ----------------------------------------------------------------------

def test_firewall_update_is_a_put_to_the_item_path():
    client, session = _build_client()
    session.queue(method="PUT", path="/firewalls/f1",
                  response=FakeResponse(payload={"firewall": {"id": "f1"}}))

    body = {"name": "fw", "inbound_rules": [], "outbound_rules": []}
    updated = client.firewalls.update(firewall_id="f1", body=body)

    call = session.calls[0]
    assert call["method"] == "PUT"
    assert call["url"].endswith("/firewalls/f1")
    # PUT is a full replacement here, so the body must be the complete state.
    assert call["body"] == body
    assert updated["firewall"]["id"] == "f1"
    return


def test_firewall_delete_addresses_the_item_path():
    client, session = _build_client()

    client.firewalls.delete(firewall_id="f1")

    assert session.calls[0]["url"].endswith("/firewalls/f1")
    return


# ----------------------------------------------------------------------
# volume actions
# ----------------------------------------------------------------------

def test_volume_action_posts_to_the_actions_subcollection():
    client, session = _build_client()
    session.queue(method="POST", path="/volumes/vol-1/actions",
                  response=FakeResponse(payload={"action": {"id": 9}}))

    body = {"type": "attach", "droplet_id": 42, "region": "nyc3"}
    result = client.volume_actions.post_by_id(volume_id="vol-1", body=body)

    call = session.calls[0]
    assert call["url"].endswith("/volumes/vol-1/actions")
    # The verb lives in the body, not the path.
    assert call["body"]["type"] == "attach"
    assert result["action"]["id"] == 9
    return


# ----------------------------------------------------------------------
# domains and records
# ----------------------------------------------------------------------

def test_list_records_addresses_the_zone():
    client, session = _build_client()
    session.queue(method="GET", path="/domains/example.com/records",
                  response=FakeResponse(
                      payload={"domain_records": [{"id": 1}]}))

    page = client.domains.list_records(domain_name="example.com",
                                       per_page=200, page=1)

    assert session.calls[0]["url"].endswith("/domains/example.com/records")
    assert page["domain_records"][0]["id"] == 1
    return


def test_create_record_posts_to_the_zone():
    client, session = _build_client()
    session.queue(method="POST", path="/domains/example.com/records",
                  response=FakeResponse(
                      status_code=201,
                      payload={"domain_record": {"id": 5}}))

    body = {"type": "A", "name": "srv-a", "data": "1.2.3.4", "ttl": 300}
    created = client.domains.create_record(domain_name="example.com",
                                           body=body)

    assert created["domain_record"]["id"] == 5
    assert session.calls[0]["body"] == body
    return


def test_delete_record_addresses_the_record_under_its_zone():
    client, session = _build_client()

    client.domains.delete_record(domain_name="example.com",
                                 domain_record_id=5)

    assert session.calls[0]["method"] == "DELETE"
    assert session.calls[0]["url"].endswith(
        "/domains/example.com/records/5")
    return


def test_domains_list_addresses_the_collection():
    client, session = _build_client()

    client.domains.list(per_page=50)

    assert session.calls[0]["url"].endswith("/domains")
    assert session.calls[0]["params"] == {"per_page": 50}
    return
