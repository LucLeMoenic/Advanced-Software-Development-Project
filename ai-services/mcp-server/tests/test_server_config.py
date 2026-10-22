"""The MCP server's DNS-rebinding allow-list is configurable for the cloud AI profile, but never into a wildcard."""

import pytest

import server


def test_the_native_defaults_are_unchanged(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)

    hosts = server.allowed_hosts()

    for expected in ("127.0.0.1:*", "localhost:*", "host.docker.internal:*"):
        assert expected in hosts
    assert not any("mcp-server" in host for host in hosts)


def test_the_bind_host_is_always_allowed(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    monkeypatch.setattr(server, "HOST", "0.0.0.0")  # noqa: S104 - a fixture value: the bind host must be allowed

    assert "0.0.0.0:*" in server.allowed_hosts()


def test_a_container_service_name_can_be_added(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp-server:*")

    assert "mcp-server:*" in server.allowed_hosts()


def test_several_entries_are_trimmed_and_blank_ones_ignored(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", " mcp-server:* , ,backend.internal:5400,  ")

    hosts = server.allowed_hosts()

    assert "mcp-server:*" in hosts and "backend.internal:5400" in hosts and "" not in hosts


def test_an_entry_already_in_the_defaults_is_not_duplicated(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "localhost:*")

    assert server.allowed_hosts().count("localhost:*") == 1


@pytest.mark.parametrize("entry", ["*", "*:*", "*.example.com", "a b", "evil.com:*:*", ":5400", "host:99999x", "-bad", "bad-", "http://mcp-server"])
def test_wildcards_and_malformed_entries_are_rejected_so_the_protection_cannot_be_switched_off(monkeypatch, entry):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", entry)

    with pytest.raises(ValueError, match="MCP_ALLOWED_HOSTS"):
        server.allowed_hosts()


def test_one_bad_entry_rejects_the_whole_setting(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp-server:*,*")

    with pytest.raises(ValueError):
        server.allowed_hosts()
