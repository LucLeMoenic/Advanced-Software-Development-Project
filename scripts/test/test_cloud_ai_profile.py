"""Offline tests for the cloud AI profile in scripts/deploy/prepare_cloud.py (bonus B1 to B4)."""

import importlib.util
import shutil
import subprocess  # noqa: S404 - fixed argv, no shell
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("prepare_cloud", ROOT / "scripts" / "deploy" / "prepare_cloud.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SHA = "a" * 40
DOMAIN = "asd.example.org"
FLAGS = {"ai": "AI_ENABLED", "mcp": "MCP_ENABLED", "rag": "RAG_ENABLED", "multi-agent": "MULTI_AGENT_ENABLED"}
URLS = {"ai": "OLLAMA_URL", "mcp": "MCP_SERVER_URL", "rag": "RAG_SERVER_URL", "multi-agent": "MULTI_AGENT_SERVER_URL"}
REACHABLE = {"ai": "http://ollama:11434", "mcp": "http://mcp-server:5400/mcp", "rag": "http://rag-server:5500",
             "multi-agent": "http://multi-agent-server:5600"}


def source():
    """The resolved integrated application, shaped like `docker compose config --format json`."""
    services = {"shared-frontend": {"build": {"context": "/source/shared"}}}
    for number in range(1, 6):
        for kind in ("frontend", "backend", "database"):
            services[f"student{number}-{kind}"] = {
                "build": {"context": "/source"}, "ports": [{"published": str(5100 + number), "target": 80}],
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "environment": {"AI_ENABLED": "true", "LITEAPI_KEY": "synthetic-placeholder"},  # pragma: allowlist secret
                **({"volumes": [{"source": "/source/data", "target": "/data"}]} if kind == "database" else {})}
    services["student3-db-init"] = {"build": {"context": "/source"}, "volumes": [{"source": "/source/data", "target": "/data"}]}
    return {"services": services}


def ai_source():
    """The resolved cloud AI profile, shaped like `docker compose config --format json` of deploy/cloud/ai.compose.yml."""
    return {"services": {
        "ollama": {"image": "ollama/ollama:0.34.3", "restart": "unless-stopped",
                   "volumes": [{"type": "volume", "source": "ollama-models", "target": "/root/.ollama"}]},
        "mcp-server": {"build": {"context": "/repo", "dockerfile": "deploy/cloud/mcp-server.Dockerfile"},
                       "environment": {"MCP_ALLOWED_HOSTS": "mcp-server:*"}, "ports": [{"published": "5400", "target": 5400}]},
        "rag-server": {"build": {"context": "/repo", "dockerfile": "deploy/cloud/rag-server.Dockerfile"},
                       "depends_on": {"ollama": {"condition": "service_healthy"}}},
        "multi-agent-server": {"build": {"context": "/repo", "dockerfile": "deploy/cloud/multi-agent-server.Dockerfile"},
                               "volumes": [{"type": "volume", "source": "multi-agent-data", "target": "/data"}],
                               "depends_on": {"ollama": {"condition": "service_healthy"}}},
    }, "volumes": {"ollama-models": {}, "multi-agent-data": {}}}


def make(components=""):
    ai = module.parse_ai_services(components)
    return module.cloud_config(source(), SHA, DOMAIN, ai, ai_source() if ai else None)


def backends(config):
    return {name: s for name, s in config["services"].items() if name.endswith("-backend")}


# -- parsing --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize(("text", "expected"), [
    ("", set()), (None, set()), (" , ", set()), ("ai", {"ai"}), (" ai , mcp ", {"ai", "mcp"}),
    ("ai,mcp,rag,multi-agent", {"ai", "mcp", "rag", "multi-agent"}), ("rag,rag", {"rag"}),
])
def test_ai_services_are_parsed_into_a_set(text, expected):
    assert module.parse_ai_services(text) == expected


@pytest.mark.parametrize("text", ["all", "AI", "llm", "ai;rm -rf /", "ai mcp", "multi_agent", "ai,,bogus"])
def test_unknown_components_are_rejected_with_the_valid_choices(text):
    with pytest.raises(ValueError, match="Choose from"):
        module.parse_ai_services(text)


@pytest.mark.parametrize(("components", "services"), [
    ("", set()), ("mcp", {"mcp-server"}), ("ai", {"ollama"}), ("rag", {"rag-server", "ollama"}),
    ("multi-agent", {"multi-agent-server", "ollama"}), ("ai,mcp,rag,multi-agent", {"ollama", "mcp-server", "rag-server", "multi-agent-server"}),
])
def test_each_component_brings_exactly_the_services_it_needs(components, services):
    assert module.ai_service_names(module.parse_ai_services(components)) == services


# -- the default is still the required baseline -----------------------------------------------------------------------------

def test_with_no_ai_services_every_capability_is_off_and_no_ai_service_exists():
    _, config, _ = make("")

    assert not set(config["services"]) & {"ollama", "mcp-server", "rag-server", "multi-agent-server"}
    for service in backends(config).values():
        env = service["environment"]
        assert all(env[flag] == "false" for flag in FLAGS.values())
        assert all(env[url] == module.UNREACHABLE for url in URLS.values())
        assert env["Services__OllamaUrl"] == module.UNREACHABLE and env["LITEAPI_KEY"] == ""
    assert set(config["volumes"]) == {"tls-data", "tls-config"}


# -- one component at a time ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("component", list(FLAGS))
def test_enabling_one_component_enables_only_that_one_on_every_backend(component):
    _, config, _ = make(component)

    for service in backends(config).values():
        env = service["environment"]
        for other, flag in FLAGS.items():
            assert env[flag] == ("true" if other == component else "false"), (other, service)
            assert env[URLS[other]] == (REACHABLE[other] if other == component else module.UNREACHABLE)


def test_enabling_all_components_points_every_backend_at_the_internal_services():
    _, config, _ = make("ai,mcp,rag,multi-agent")

    for service in backends(config).values():
        env = service["environment"]
        assert all(env[flag] == "true" for flag in FLAGS.values())
        assert {env[url] for url in URLS.values()} == set(REACHABLE.values())
        assert env["Services__OllamaUrl"] == "http://ollama:11434"


def test_student_3_uses_the_single_cloud_model_only_when_ai_mode_is_on():
    assert "OLLAMA_MODEL" not in make("mcp")[1]["services"]["student3-backend"]["environment"]
    assert make("ai")[1]["services"]["student3-backend"]["environment"]["OLLAMA_MODEL"] == module.CLOUD_MODEL == "llama3.2:3b"


def test_the_sandbox_api_key_stays_blank_with_every_ai_component_enabled():
    _, config, _ = make("ai,mcp,rag,multi-agent")

    assert all(s["environment"]["LITEAPI_KEY"] == "" for s in backends(config).values())


# -- the AI services themselves ---------------------------------------------------------------------------------------------

def test_ai_services_never_publish_a_port_even_if_their_definition_does():
    build, config, _ = make("ai,mcp,rag,multi-agent")

    for name in ("ollama", "mcp-server", "rag-server", "multi-agent-server"):
        assert "ports" not in config["services"][name] and "ports" not in build["services"][name]
    assert [n for n, s in config["services"].items() if s.get("ports")] == ["tls-gateway"]
    assert config["networks"]["private"]["internal"] is True


def test_only_ollama_has_outbound_access_so_it_can_pull_models_and_nothing_else_does():
    _, config, _ = make("ai,mcp,rag,multi-agent")

    assert config["services"]["ollama"]["networks"] == ["private", "egress"]
    assert "internal" not in config["networks"]["egress"]  # a normal bridge: outbound works, nothing is published
    for name, service in config["services"].items():
        if name not in ("ollama", "tls-gateway"):
            assert service["networks"] == ["private"], name
    assert [n for n, s in config["services"].items() if "egress" in s["networks"]] == ["ollama"]


def test_without_ollama_there_is_no_egress_network_at_all():
    for components in ("", "mcp"):
        assert "egress" not in make(components)[1]["networks"]


def test_the_egress_network_exists_whenever_ollama_does():
    for components in ("ai", "rag", "multi-agent"):
        _, config, _ = make(components)

        assert "egress" in config["networks"] and "egress" in config["services"]["ollama"]["networks"]


def test_built_ai_images_are_named_by_revision_and_ollama_keeps_its_pinned_upstream_image():
    build, config, _ = make("ai,mcp,rag,multi-agent")

    for name in ("mcp-server", "rag-server", "multi-agent-server"):
        assert config["services"][name]["image"] == f"asd-{name}:{SHA}"
        assert "build" in build["services"][name] and "build" not in config["services"][name]
    assert config["services"]["ollama"]["image"] == "ollama/ollama:0.34.3" and "build" not in build["services"]["ollama"]


def test_the_vm_pulls_ollama_instead_of_the_runner_shipping_it():
    build, config, _ = make("ai,mcp,rag,multi-agent")

    shipped, pulled = module.split_images(config, build, module.parse_ai_services("ai,mcp,rag,multi-agent"))

    assert pulled == ["ollama/ollama:0.34.3"] and "ollama/ollama:0.34.3" not in shipped
    for image in (f"asd-mcp-server:{SHA}", f"asd-rag-server:{SHA}", f"asd-multi-agent-server:{SHA}",
                  f"asd-student3-backend:{SHA}", "caddy:2.10.2-alpine"):
        assert image in shipped


def test_without_ai_nothing_is_pulled_by_the_vm_and_everything_is_shipped_as_before():
    build, config, _ = make("")

    shipped, pulled = module.split_images(config, build, frozenset())

    assert pulled == [] and len(shipped) == len(config["services"])


def test_volumes_are_declared_only_for_the_services_that_use_them():
    assert set(make("mcp")[1]["volumes"]) == {"tls-data", "tls-config"}
    assert set(make("ai")[1]["volumes"]) == {"tls-data", "tls-config", "ollama-models"}
    assert set(make("multi-agent")[1]["volumes"]) == {"tls-data", "tls-config", "ollama-models", "multi-agent-data"}


def test_rag_and_multi_agent_wait_for_a_healthy_ollama_and_it_is_always_included():
    for component in ("rag", "multi-agent"):
        _, config, _ = make(component)

        assert "ollama" in config["services"]
        assert config["services"][f"{component}-server" if component == "rag" else "multi-agent-server"]["depends_on"]["ollama"]["condition"] == "service_healthy"


def test_the_gateway_and_caddyfile_are_unchanged_by_the_ai_profile():
    _, base_config, base_caddy = make("")
    _, ai_config, ai_caddy = make("ai,mcp,rag,multi-agent")

    assert ai_caddy == base_caddy and ai_config["services"]["tls-gateway"] == base_config["services"]["tls-gateway"]


# -- refusing to produce a half-defined bundle --------------------------------------------------------------------------------

def test_an_ai_component_without_a_profile_is_refused():
    with pytest.raises(ValueError, match="does not define"):
        module.cloud_config(source(), SHA, DOMAIN, module.parse_ai_services("rag"), None)


def test_a_profile_missing_a_needed_service_is_refused():
    partial = ai_source()
    del partial["services"]["ollama"]

    with pytest.raises(ValueError, match="does not define"):
        module.cloud_config(source(), SHA, DOMAIN, module.parse_ai_services("rag"), partial)


def test_an_unknown_component_passed_directly_is_refused():
    with pytest.raises(ValueError, match="Unknown AI component"):
        module.cloud_config(source(), SHA, DOMAIN, frozenset({"telepathy"}), ai_source())


def test_the_existing_revision_and_domain_checks_still_apply_with_ai_enabled():
    with pytest.raises(ValueError):
        module.cloud_config(source(), "main", DOMAIN, module.parse_ai_services("ai"), ai_source())
    with pytest.raises(ValueError):
        module.cloud_config(source(), SHA, "https://example.org", module.parse_ai_services("ai"), ai_source())


# -- the real profile file --------------------------------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker with Compose is required")
def test_the_real_ai_compose_file_is_valid_defines_all_four_services_and_publishes_nothing():
    result = subprocess.run(  # noqa: S603 - resolved docker executable, fixed arguments
        [shutil.which("docker"), "compose", "-f", str(ROOT / "deploy" / "cloud" / "ai.compose.yml"), "config", "--format", "json"],
        capture_output=True, text=True, check=False, timeout=60)
    assert result.returncode == 0, result.stderr
    import json
    services = json.loads(result.stdout)["services"]

    assert set(services) == {"ollama", "mcp-server", "rag-server", "multi-agent-server"}
    assert not any(s.get("ports") for s in services.values())
    assert services["ollama"]["image"] == "ollama/ollama:0.34.3"
    assert services["mcp-server"]["environment"]["MCP_ALLOWED_HOSTS"] == "mcp-server:*"
