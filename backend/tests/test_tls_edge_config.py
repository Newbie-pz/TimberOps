"""Static edge-policy and private-key governance tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from starlette.datastructures import Headers

from app.middleware.request_logging import _resolve_client_ip

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIRECTORY = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIRECTORY))
security_check = importlib.import_module("security_check")


def test_tls_nginx_enables_modern_protocols_and_https_only_hsts() -> None:
    tls_config = (ROOT / "frontend" / "nginx.tls.conf").read_text(encoding="utf-8")
    http_config = (ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")

    assert "listen 443 ssl;" in tls_config
    assert "ssl_protocols TLSv1.2 TLSv1.3;" in tls_config
    assert "Strict-Transport-Security" in tls_config
    assert "Strict-Transport-Security" not in http_config


def test_tls_http_redirect_preserves_path_and_query() -> None:
    tls_config = (ROOT / "frontend" / "nginx.tls.conf").read_text(encoding="utf-8")

    assert "return 308 https://$host$request_uri;" in tls_config


def test_public_edge_blocks_metrics_and_rewrites_forwarding_chain() -> None:
    for config_path in (
        ROOT / "frontend" / "nginx.conf",
        ROOT / "frontend" / "nginx.tls.conf",
    ):
        config = config_path.read_text(encoding="utf-8")
        assert "location = /metrics" in config
        assert "proxy_set_header X-Forwarded-For $remote_addr;" in config
        assert "$proxy_add_x_forwarded_for" not in config

    production_compose = (ROOT / "docker-compose.prod.yml").read_text(
        encoding="utf-8"
    )
    assert 'FORWARDED_ALLOW_IPS: "*"' in production_compose
    assert 'expose:\n      - "8000"' in production_compose
    assert '8000:8000' not in production_compose


def test_request_logger_trusts_real_ip_only_from_internal_proxy() -> None:
    headers = Headers({"X-Real-IP": "198.51.100.25"})

    assert (
        _resolve_client_ip({"client": ("172.20.0.10", 1234)}, headers)  # type: ignore[arg-type]
        == "198.51.100.25"
    )
    assert (
        _resolve_client_ip({"client": ("203.0.113.10", 1234)}, headers)  # type: ignore[arg-type]
        == "203.0.113.10"
    )


def test_security_scan_detects_private_key_without_flagging_public_fixture(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(security_check, "ROOT", tmp_path)
    private_key = tmp_path / "server.key"
    private_key.write_text(
        "-----BEGIN PRIVATE KEY-----\ndo-not-log-this-material\n"
        "-----END PRIVATE KEY-----\n",
        encoding="utf-8",
    )
    public_certificate = tmp_path / "tests" / "fixtures" / "public.crt"
    public_certificate.parent.mkdir(parents=True)
    public_certificate.write_text(
        "-----BEGIN CERTIFICATE-----\npublic-test-fixture\n"
        "-----END CERTIFICATE-----\n",
        encoding="utf-8",
    )

    findings = security_check._scan_tracked_certificate_material(
        [private_key, public_certificate]
    )

    assert len(findings) == 1
    assert findings[0].level == "FAIL"
    assert "server.key" in findings[0].message
    assert "do-not-log-this-material" not in findings[0].message
