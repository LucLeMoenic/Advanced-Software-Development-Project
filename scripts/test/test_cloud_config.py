import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("prepare_cloud", Path(__file__).resolve().parents[1] / "deploy" / "prepare_cloud.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def source():
    services = {"shared-frontend": {"build": {"context": "/source/shared"}}}
    for number in range(1, 6):
        for kind in ("frontend", "backend", "database"):
            services[f"student{number}-{kind}"] = {"build": {"context": "/source"},
                "ports": [{"published": str(5100 + number), "target": 80}], "extra_hosts": ["host.docker.internal:host-gateway"],
                "environment": {"AI_ENABLED": "true", "LITEAPI_KEY": "synthetic-placeholder"},  # pragma: allowlist secret
                **({"volumes": [{"source": "/source/data", "target": "/data"}]} if kind == "database" else {})}
    services["student3-db-init"] = {"build": {"context": "/source"}, "volumes": [{"source": "/source/data", "target": "/data"}]}
    return {"services": services}


def test_cloud_preserves_services_disables_ai_and_isolates_networks():
    build, config, caddy = module.cloud_config(source(), "a" * 40, "asd.example.org")
    assert len(config["services"]) == 18
    assert config["networks"]["private"]["internal"] is True
    assert "reverse_proxy shared-frontend:80" in caddy
    for name, service in config["services"].items():
        assert "build" not in service
        if name != "tls-gateway":
            assert "ports" not in service and "extra_hosts" not in service
            assert service["networks"] == ["private"]
            assert service["image"].endswith("a" * 40)
            assert "build" in build["services"][name]
        if name.endswith("-backend"):
            assert service["environment"]["LITEAPI_KEY"] == ""
            assert all(service["environment"][flag] == "false" for flag in (
                "AI_ENABLED", "MCP_ENABLED", "RAG_ENABLED", "MULTI_AGENT_ENABLED"))
        if "database" in name or name == "student3-db-init":
            assert service["volumes"][0]["source"].startswith("/opt/asd/data/student-")


@pytest.mark.parametrize("sha,domain", [("main", "asd.example.org"), ("a" * 40, "https://example.org"),
                                      ("a" * 40, "bad\nconfig"), ("a" * 40, "../path")])
def test_cloud_rejects_untrusted_revision_and_domain(sha, domain):
    with pytest.raises(ValueError):
        module.cloud_config(source(), sha, domain)


def test_cloud_refuses_partial_application_or_unknown_storage():
    value = source()
    del value["services"]["student2-backend"]
    with pytest.raises(ValueError):
        module.cloud_config(value, "a" * 40, "asd.example.org")
    value = source()
    value["services"]["student2-database"]["volumes"][0]["target"] = "/elsewhere"
    with pytest.raises(ValueError):
        module.cloud_config(value, "a" * 40, "asd.example.org")
