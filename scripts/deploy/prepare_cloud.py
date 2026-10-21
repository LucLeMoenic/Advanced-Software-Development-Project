"""Build an immutable, AI-disabled Compose bundle for an approved Azure or AWS Linux VM."""

import argparse
import copy
import json
import re
import shutil
import subprocess  # noqa: S404 - fixed Docker argv, no shell
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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


def cloud_config(source, sha, domain):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("A complete lowercase commit SHA is required.")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", domain) or "." not in domain or ".." in domain:
        raise ValueError("Use the approved public DNS hostname, without a scheme or path.")
    expected = {"shared-frontend", "student3-db-init"} | {
        f"student{i}-{kind}" for i in range(1, 6) for kind in ("frontend", "backend", "database")}
    if set(source["services"]) != expected:
        raise ValueError("Cloud preparation requires the complete known integrated application.")
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
            environment.update({flag: "false" for flag in ("AI_ENABLED", "MCP_ENABLED", "RAG_ENABLED", "MULTI_AGENT_ENABLED")})
            for setting in ("OLLAMA_URL", "Services__OllamaUrl", "MCP_SERVER_URL", "RAG_SERVER_URL", "MULTI_AGENT_SERVER_URL"):
                environment[setting] = "http://127.0.0.1:9"
            environment["LITEAPI_KEY"] = ""
        if service.get("volumes"):
            student = re.fullmatch(r"student([1-5])-(?:database|db-init)", name)
            if not student or len(service["volumes"]) != 1 or service["volumes"][0]["target"] != "/data":
                raise ValueError(f"Unexpected persistent storage contract for {name}.")
            service["volumes"] = [{"type": "bind", "source": f"/opt/asd/data/student-{student[1]}", "target": "/data"}]
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("Docker with Compose must be installed.")
    result = subprocess.run(  # noqa: S603 - resolved Docker executable and fixed arguments
        [docker, "compose", "--env-file", str(ROOT / ".env.example"), "config", "--format", "json"],
        cwd=ROOT, capture_output=True, text=True, check=True)
    build, config, caddy = cloud_config(json.loads(result.stdout), args.sha, args.domain)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "compose-build.json").write_text(json.dumps(build, indent=2), encoding="utf-8")
    (args.output / "compose.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (args.output / "Caddyfile").write_text(caddy, encoding="utf-8")
    (args.output / "revision.txt").write_text(args.sha + "\n", encoding="utf-8")
    (args.output / "images.txt").write_text("\n".join(s["image"] for s in config["services"].values()) + "\n", encoding="utf-8")
    shutil.copyfile(ROOT / "student-1/database/storage/accommodation.db", args.output / "accommodation.db")
    for filename in ("deploy-vm.sh", "smoke_cloud.py"):
        shutil.copyfile(Path(__file__).with_name(filename), args.output / filename)
    print(f"Prepared {len(config['services'])} cloud services with AI disabled; no resources were provisioned.")


if __name__ == "__main__":
    main()
