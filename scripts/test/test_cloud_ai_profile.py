"""Offline tests for the cloud AI profile in scripts/deploy/prepare_cloud.py (bonus B1 to B4)."""

import importlib.util
import json
import shutil
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
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

def test_cloud_ai_deadlines_are_wired_end_to_end_without_changing_baseline():
    baseline_build, baseline, _ = make()
    build, enabled, _ = make("ai,mcp,rag,multi-agent")
    assert all(s["environment"]["CLOUD_AI_SLOW_MODE"] == "false" for s in backends(baseline).values())
    assert all(s["environment"]["CLOUD_AI_SLOW_MODE"] == "true" for s in backends(enabled).values())
    assert enabled["services"]["rag-server"]["environment"]["CLOUD_AI_SLOW_MODE"] == "true"
    assert enabled["services"]["student3-backend"]["environment"]["OLLAMA_TIMEOUT"] == "180"
    assert "configs" not in baseline
    assert "VITE_CLOUD_AI_SLOW_MODE" not in baseline_build["services"]["student2-frontend"]["build"].get("args", {})
    assert build["services"]["student2-frontend"]["build"]["args"]["VITE_CLOUD_AI_SLOW_MODE"] == "true"
    assert enabled["services"]["student2-frontend"]["image"] == f"asd-student2-frontend:{SHA}-ai"
    assert baseline["services"]["student2-frontend"]["image"] == f"asd-student2-frontend:{SHA}"
    assert len(enabled["configs"]) == 6
    for name, value in enabled["configs"].items():
        content = value["content"]
        assert "proxy_read_timeout 400s;" in content and "proxy_send_timeout 400s;" in content
        assert "$$" in content
        service = enabled["services"][name.removesuffix("-nginx")]
        assert service["configs"][0]["source"] == name
        assert service["configs"][0]["target"].startswith("/etc/nginx/")


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


def test_enabled_ai_uses_the_provisioned_model_even_if_local_tags_differ():
    app = source()
    for number in (1, 2, 5):
        app["services"][f"student{number}-backend"]["environment"]["APPLICATION_MODEL"] = "local-only:7b"
    app["services"]["student4-backend"]["environment"]["STUDENT4_MODEL"] = "local-only:7b"
    _, config, _ = module.cloud_config(app, SHA, DOMAIN, {"ai"}, ai_source())
    for number in (1, 2, 5):
        assert config["services"][f"student{number}-backend"]["environment"]["APPLICATION_MODEL"] == module.CLOUD_MODEL
    assert config["services"]["student4-backend"]["environment"]["STUDENT4_MODEL"] == module.CLOUD_MODEL


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


def test_only_ollama_and_mcp_have_outbound_access_for_models_and_weather():
    _, config, _ = make("ai,mcp,rag,multi-agent")

    assert config["services"]["ollama"]["networks"] == ["private", "egress"]
    assert config["services"]["mcp-server"]["networks"] == ["private", "egress"]
    assert "internal" not in config["networks"]["egress"]  # a normal bridge: outbound works, nothing is published
    for name, service in config["services"].items():
        if name not in ("ollama", "mcp-server", "tls-gateway"):
            assert service["networks"] == ["private"], name
    assert {n for n, s in config["services"].items() if "egress" in s["networks"]} == {"ollama", "mcp-server"}


def test_baseline_has_no_egress_network():
    assert "egress" not in make("")[1]["networks"]


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


def test_ai_gateway_requires_private_auth_without_putting_credentials_in_the_bundle():
    _, base_config, base_caddy = make("")
    _, ai_config, ai_caddy = make("ai,mcp,rag,multi-agent")

    assert "gateway-auth.caddy" not in base_caddy
    assert "import /etc/caddy/gateway-auth.caddy" in ai_caddy
    assert "header_up -Authorization" in ai_caddy
    mount = ai_config["services"]["tls-gateway"]["volumes"][-1]
    assert mount["source"] == "./gateway-auth.caddy" and mount["read_only"]
    assert mount["bind"]["create_host_path"] is False
    assert base_config["services"]["tls-gateway"]["ports"] == ai_config["services"]["tls-gateway"]["ports"]


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
def test_cloud_multi_agent_deadline_reaches_bundle_and_fits_smoke_budgets():
    import smoke_cloud_ai

    result = subprocess.run(  # noqa: S603 - resolved docker executable, fixed arguments
        [shutil.which("docker"), "compose", "-f", str(ROOT / "deploy" / "cloud" / "ai.compose.yml"), "config", "--format", "json"],
        capture_output=True, text=True, check=False, timeout=60)
    assert result.returncode == 0, result.stderr
    profile = json.loads(result.stdout)
    services = profile["services"]
    assert set(services) == {"ollama", "mcp-server", "rag-server", "multi-agent-server"}
    assert not any(s.get("ports") for s in services.values())
    assert services["ollama"]["image"] == "ollama/ollama:0.34.3"
    assert services["mcp-server"]["environment"]["MCP_ALLOWED_HOSTS"] == "mcp-server:*"

    _, config, _ = module.cloud_config(source(), SHA, DOMAIN, frozenset({"multi-agent"}), profile)
    deadline = int(config["services"]["multi-agent-server"]["environment"]["MULTI_AGENT_TIMEOUT"])
    assert deadline == 360
    assert smoke_cloud_ai.WORKFLOW_TIMEOUT >= 3 * 2 * deadline + 60
    workflow = (ROOT / ".github" / "workflows" / "cloud-deployment.yml").read_text()
    smoke_step = next(step for step in workflow.split("      - name: ")
                      if step.startswith("Verify protected group CRUD and AI integrations\n"))
    step_minutes = int(next(line.split(":", 1)[1] for line in smoke_step.splitlines()
                            if line.startswith("        timeout-minutes:")))
    assert step_minutes * 60 >= 4 * smoke_cloud_ai.WORKFLOW_TIMEOUT + 3600
    _, baseline, _ = make()
    assert "multi-agent-server" not in baseline["services"]


@pytest.mark.parametrize("components", ["", "ai,mcp,rag,multi-agent"])
def test_preparation_ships_model_provisioning_metadata_and_both_smoke_scripts(tmp_path, monkeypatch, components):
    output = tmp_path / "bundle"
    calls = []

    def compose(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(ai_source() if "-f" in argv else source()))

    monkeypatch.setattr(module.shutil, "which", lambda name: "docker")
    monkeypatch.setattr(module.subprocess, "run", compose)
    monkeypatch.setattr(sys, "argv", ["prepare_cloud.py", "--sha", SHA, "--domain", DOMAIN,
                                    "--ai-services", components, "--output", str(output)])
    module.main()

    assert len(calls) == (2 if components else 1)
    assert (output / "ai-services.txt").read_text().strip() == ",".join(sorted(module.parse_ai_services(components)))
    assert (output / "vm-pull-images.txt").read_text().splitlines() == (["ollama/ollama:0.34.3"] if components else [])
    assert "ollama/ollama:0.34.3" not in (output / "images.txt").read_text()
    for filename in ("deploy-vm.sh", "pull-models-vm.sh", "smoke_cloud.py", "smoke_cloud_ai.py", "cloud_auth.py"):
        assert (output / filename).read_bytes() == (ROOT / "scripts" / "deploy" / filename).read_bytes()


def test_ai_preparation_workflow_never_connects_to_or_tests_the_public_vm():
    text = (ROOT / ".github" / "workflows" / "cloud-deployment.yml").read_text()
    assert "default: baseline" in text
    assert "          - prepare-ai" in text
    assert "          - ai\n" in text
    assert "--ai-services \"$CLOUD_AI_SERVICES\"" in text
    steps = text.split("      - name: ")
    for name in ("Configure pinned SSH access", "Deploy to the approved Azure or AWS Linux VM",
                 "Wait for public HTTPS readiness"):
        step = next(step for step in steps if step.startswith(name + "\n"))
        assert "        if: inputs.mode != 'prepare-ai'\n" in step, name
    package = next(step for step in steps if step.startswith("Package AI preparation without deployment\n"))
    assert "if: inputs.mode == 'prepare-ai'" in package
    assert "tar -cf cloud-ai-bundle.tar" in package
    assert "gateway-auth.caddy" not in package
    ai_smoke = next(step for step in steps if step.startswith("Verify protected group CRUD and AI integrations\n"))
    assert "if: inputs.mode == 'ai'" in ai_smoke
    assert "--all-features" in ai_smoke
    for name in ("Require protected AI credentials", "Prepare private gateway credentials"):
        step = next(step for step in steps if step.startswith(name + "\n"))
        assert "if: inputs.mode == 'ai'" in step
        assert "secrets.CLOUD_AUTH_USER" in step and "secrets.CLOUD_AUTH_PASSWORD" in step
    evidence = next(step for step in steps if step.startswith("Retain deployment evidence\n"))
    assert "gateway-auth.caddy" not in evidence and "CLOUD_AUTH_PASSWORD" not in evidence
    readiness = next(step for step in steps if step.startswith("Wait for public HTTPS readiness\n"))
    assert "--required" in readiness and 'cloud_auth.py verify' in readiness
    build = next(step for step in steps if step.startswith("Build immutable application images\n"))
    deploy = next(step for step in steps if step.startswith("Deploy to the approved Azure or AWS Linux VM\n"))
    for filename in ("smoke_cloud_ai.py", "pull-models-vm.sh", "ai-services.txt", "vm-pull-images.txt"):
        assert filename in build and filename in deploy and filename in package
