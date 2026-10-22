"""Build an immutable Compose bundle for an approved Azure or AWS Linux VM.

By default every AI capability is disabled (the required cloud baseline). With --ai-services the chosen cloud AI
components (bonus B1 to B4) are added from deploy/cloud/ai.compose.yml and enabled on the backends.
"""

import argparse
import copy
import json
import re
import shutil
import subprocess  # noqa: S404 - fixed Docker argv, no shell
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Cloud AI profile (bonus B1 to B4). Each component is enabled on its own; none is enabled by default.
AI_COMPONENTS = ("ai", "mcp", "rag", "multi-agent")  # AI-Mode (Ollama), MCP, RAG, Multi-Agent
AI_SERVER_FOR = {"mcp": "mcp-server", "rag": "rag-server", "multi-agent": "multi-agent-server"}
NEEDS_OLLAMA = frozenset({"ai", "rag", "multi-agent"})
UNREACHABLE = "http://127.0.0.1:9"  # nothing listens here: a disabled service is unreachable, not just switched off
CLOUD_MODEL = "llama3.2:3b"  # one model for every consumer, so a single model is resident in the VM's memory
AI_COMPOSE = ROOT / "deploy" / "cloud" / "ai.compose.yml"


def parse_ai_services(value):
    """'ai,mcp' -> frozenset({'ai', 'mcp'}); '' -> empty. Only the four known components are accepted."""
    items = [part.strip() for part in (value or "").split(",") if part.strip()]
    unknown = [item for item in items if item not in AI_COMPONENTS]
    if unknown:
        raise ValueError(f"Unknown AI component(s): {', '.join(unknown)}. Choose from: {', '.join(AI_COMPONENTS)}.")
    return frozenset(items)


def ai_service_names(ai):
    """The cloud-only Compose services the chosen components need. Ollama serves AI-Mode, RAG and Multi-Agent."""
    names = {AI_SERVER_FOR[component] for component in ai if component in AI_SERVER_FOR}
    if ai & NEEDS_OLLAMA:
        names.add("ollama")
    return names


CADDYFILE = """{{DOMAIN}} {
	# Automatic HTTPS: certificate issued and renewed by Caddy, HTTP redirected to HTTPS, TLS 1.2 minimum.
	encode zstd gzip

	# Endpoint hardening. Only the verbs the applications use are accepted.
	@disallowed not method GET HEAD POST PUT PATCH DELETE OPTIONS
	respond @disallowed "Method not allowed" 405

	# The applications exchange small JSON documents; refuse anything larger before it reaches a backend.
	request_body {
		max_size 1MB
	}

	header {
		Strict-Transport-Security "max-age=31536000; includeSubDomains"
		X-Content-Type-Options "nosniff"
		X-Frame-Options "DENY"
		Referrer-Policy "strict-origin-when-cross-origin"
		Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()"
		# Only the directives the pages can already satisfy. The UIs use inline scripts and CDN scripts, so a
		# script-src policy is deliberately not applied here.
		Content-Security-Policy "frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'"
		-Server
	}

	reverse_proxy shared-frontend:80 {
		# Overwrite any client-supplied value so the gateway's per-client rate limit cannot be dodged by forging it.
		header_up X-Forwarded-For {remote_host}
	}
}
"""


def caddyfile(domain):
    """The hardened Caddyfile for the public TLS gateway (the only service with published ports)."""
    return CADDYFILE.replace("{{DOMAIN}}", domain)


def cloud_config(source, sha, domain, ai=frozenset(), ai_source=None):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("A complete lowercase commit SHA is required.")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", domain) or "." not in domain or ".." in domain:
        raise ValueError("Use the approved public DNS hostname, without a scheme or path.")
    expected = {"shared-frontend", "student3-db-init"} | {
        f"student{i}-{kind}" for i in range(1, 6) for kind in ("frontend", "backend", "database")}
    if set(source["services"]) != expected:
        raise ValueError("Cloud preparation requires the complete known integrated application.")
    ai = frozenset(ai)
    wanted = ai_service_names(ai)
    if not ai <= set(AI_COMPONENTS):
        raise ValueError("Unknown AI component requested.")
    if wanted and (ai_source is None or not wanted <= set(ai_source["services"])):
        raise ValueError("The cloud AI profile does not define every service the chosen components need.")
    config = {"name": "asd-cloud", "services": copy.deepcopy(source["services"]),
              "networks": {"private": {"internal": True}, "public": {}},
              "volumes": {"tls-data": {}, "tls-config": {}}}
    for name, service in config["services"].items():
        service["image"] = f"asd-{name}:{sha}"
        service.pop("ports", None)
        service.pop("extra_hosts", None)
        service["networks"] = ["private"]
        environment = service.setdefault("environment", {})
        if name.endswith("-backend"):
            switches = {"AI_ENABLED": "ai", "MCP_ENABLED": "mcp", "RAG_ENABLED": "rag", "MULTI_AGENT_ENABLED": "multi-agent"}
            environment.update({flag: "true" if component in ai else "false" for flag, component in switches.items()})
            ollama = "http://ollama:11434" if "ai" in ai else UNREACHABLE
            environment.update({
                "OLLAMA_URL": ollama, "Services__OllamaUrl": ollama,
                "MCP_SERVER_URL": "http://mcp-server:5400/mcp" if "mcp" in ai else UNREACHABLE,
                "RAG_SERVER_URL": "http://rag-server:5500" if "rag" in ai else UNREACHABLE,
                "MULTI_AGENT_SERVER_URL": "http://multi-agent-server:5600" if "multi-agent" in ai else UNREACHABLE,
            })
            if "ai" in ai and name == "student3-backend":
                environment["OLLAMA_MODEL"] = CLOUD_MODEL
            environment["LITEAPI_KEY"] = ""
        if service.get("volumes"):
            student = re.fullmatch(r"student([1-5])-(?:database|db-init)", name)
            if not student or len(service["volumes"]) != 1 or service["volumes"][0]["target"] != "/data":
                raise ValueError(f"Unexpected persistent storage contract for {name}.")
            service["volumes"] = [{"type": "bind", "source": f"/opt/asd/data/student-{student[1]}", "target": "/data"}]
    for name in sorted(wanted):  # the cloud-only AI services: internal network, never a published port
        service = copy.deepcopy(ai_source["services"][name])
        service.pop("ports", None)
        service.pop("extra_hosts", None)
        service["networks"] = ["private"]
        if name == "ollama":
            # The private network is internal (no outbound access), so Ollama could never download a model. Give it, and only
            # it, a second non-internal network for pulling models. Nothing is published and no other service gets egress.
            service["networks"] = ["private", "egress"]
            config["networks"]["egress"] = {}
        if "build" in service:  # built from this repository like the application services
            service["image"] = f"asd-{name}:{sha}"
        config["services"][name] = service
    for volume in ai_source.get("volumes", {}) if wanted else {}:
        if any(volume == (v.get("source") if isinstance(v, dict) else v) for name in wanted
               for v in config["services"][name].get("volumes", [])):
            config["volumes"][volume] = {}
    config["services"]["tls-gateway"] = {
        "image": "caddy:2.10.2-alpine", "restart": "unless-stopped",
        "ports": ["80:80", "443:443"], "networks": ["private", "public"],
        "volumes": ["./Caddyfile:/etc/caddy/Caddyfile:ro", "tls-data:/data", "tls-config:/config"],
        "depends_on": {"shared-frontend": {"condition": "service_healthy"}},
    }
    build = copy.deepcopy(config)
    for service in config["services"].values():
        service.pop("build", None)
    return build, config, caddyfile(domain)


def split_images(config, build, ai):
    """(images the runner ships, images the VM pulls itself).

    Upstream AI images (Ollama, about 8 GB) are pulled by the VM from the registry; shipping them through the runner as part of
    images.tar over SSH would be wasteful. Everything built from this repository, and the TLS gateway image, is shipped as before.
    """
    pulled = [service["image"] for name, service in build["services"].items()
              if name in ai_service_names(ai) and "build" not in service]
    shipped = [service["image"] for service in config["services"].values() if service["image"] not in pulled]
    return shipped, pulled


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ai-services", default="", help="comma list of cloud AI components to enable: " + ", ".join(AI_COMPONENTS))
    args = parser.parse_args()
    ai = parse_ai_services(args.ai_services)
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("Docker with Compose must be installed.")
    result = subprocess.run(  # noqa: S603 - resolved Docker executable and fixed arguments
        [docker, "compose", "--env-file", str(ROOT / ".env.example"), "config", "--format", "json"],
        cwd=ROOT, capture_output=True, text=True, check=True)
    ai_source = None
    if ai:
        ai_result = subprocess.run(  # noqa: S603 - resolved Docker executable and fixed arguments
            [docker, "compose", "--env-file", str(ROOT / ".env.example"), "-f", str(AI_COMPOSE), "config", "--format", "json"],
            cwd=ROOT, capture_output=True, text=True, check=True)
        ai_source = json.loads(ai_result.stdout)
    build, config, caddy = cloud_config(json.loads(result.stdout), args.sha, args.domain, ai, ai_source)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "compose-build.json").write_text(json.dumps(build, indent=2), encoding="utf-8")
    (args.output / "compose.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (args.output / "Caddyfile").write_text(caddy, encoding="utf-8")
    (args.output / "revision.txt").write_text(args.sha + "\n", encoding="utf-8")
    shipped, vm_pulled = split_images(config, build, ai)
    (args.output / "images.txt").write_text("\n".join(shipped) + "\n", encoding="utf-8")
    (args.output / "vm-pull-images.txt").write_text("".join(f"{image}\n" for image in vm_pulled), encoding="utf-8")
    (args.output / "ai-services.txt").write_text(",".join(sorted(ai)) + "\n", encoding="utf-8")
    shutil.copyfile(ROOT / "student-1/database/storage/accommodation.db", args.output / "accommodation.db")
    for filename in ("deploy-vm.sh", "smoke_cloud.py"):
        shutil.copyfile(Path(__file__).with_name(filename), args.output / filename)
    mode = f"cloud AI components enabled: {', '.join(sorted(ai))}" if ai else "AI disabled"
    print(f"Prepared {len(config['services'])} cloud services ({mode}); no resources were provisioned.")


if __name__ == "__main__":
    main()
