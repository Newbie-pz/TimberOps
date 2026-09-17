"""Run a lightweight, redacting security check for TimberOps configuration."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
PLACEHOLDER_PREFIXES = ("replace_", "change_me", "your_", "example_")
SCAN_SUFFIXES = {".py", ".ts", ".vue", ".js", ".yml", ".yaml", ".toml", ".ini", ".sh"}
HIGH_CONFIDENCE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
)
LITERAL_SECRET_PATTERN = re.compile(
    r"(?i)\b(?:api[_-]?key|password|secret|token)\b\s*[:=]\s*"
    r"(?P<quote>['\"])(?P<value>[^'\"]{8,})(?P=quote)"
)


@dataclass(frozen=True)
class Finding:
    level: str
    message: str


def _git_tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        ROOT / item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    ]


def _git_visible_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        ROOT / item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    ]


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return not normalized or normalized.startswith(PLACEHOLDER_PREFIXES) or normalized in {
        "secret",
        "changeme",
        "development",
    }


def _scan_tracked_sources(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    excluded_parts = {"tests", "node_modules", ".git", "dist"}
    for path in paths:
        relative = path.relative_to(ROOT)
        if (
            path.name in {"package-lock.json", "pnpm-lock.yaml", ".env.example"}
            or path == Path(__file__).resolve()
            or excluded_parts.intersection(relative.parts)
            or (path.suffix not in SCAN_SUFFIXES and path.name != "Dockerfile")
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in HIGH_CONFIDENCE_PATTERNS):
                findings.append(
                    Finding(
                        "FAIL",
                        f"possible API key or JWT in {relative}:{line_number}",
                    )
                )
            match = LITERAL_SECRET_PATTERN.search(line)
            if match and not _is_placeholder(match.group("value")):
                findings.append(
                    Finding(
                        "FAIL",
                        f"possible hard-coded credential in {relative}:{line_number}",
                    )
                )
    return findings


def run_checks() -> list[Finding]:
    """Return redacted findings without ever including a secret value."""
    findings: list[Finding] = []
    try:
        tracked_files = _git_tracked_files()
        visible_files = _git_visible_files()
    except (OSError, subprocess.CalledProcessError):
        return [Finding("FAIL", "unable to inspect Git tracked files")]

    tracked_names = {
        path.relative_to(ROOT).as_posix()
        for path in tracked_files
    }
    if ".env" in tracked_names:
        findings.append(Finding("FAIL", ".env is tracked by Git"))
    else:
        findings.append(Finding("PASS", ".env is not tracked by Git"))

    source_findings = _scan_tracked_sources(visible_files)
    findings.extend(source_findings)
    if not source_findings:
        findings.append(
            Finding("PASS", "no high-confidence credentials found in repository runtime files")
        )

    example_values = _parse_env(ROOT / ".env.example")
    example_secret_failure = False
    for key in ("JWT_SECRET_KEY", "POSTGRES_PASSWORD"):
        value = example_values.get(key, "")
        if value and not _is_placeholder(value):
            example_secret_failure = True
    if example_values.get("DOUBAO_API_KEY"):
        example_secret_failure = True
    for key in ("DATABASE_URL", "DATABASE_URL_DOCKER"):
        password = urlsplit(example_values.get(key, "")).password
        if password and not _is_placeholder(password):
            example_secret_failure = True
    if example_secret_failure:
        findings.append(Finding("FAIL", ".env.example appears to contain a real secret"))
    else:
        findings.append(Finding("PASS", ".env.example contains placeholders only"))

    if not ENV_FILE.exists():
        findings.append(Finding("WARN", ".env does not exist; runtime secrets were not validated"))
        return findings

    env = _parse_env(ENV_FILE)
    jwt_secret = env.get("JWT_SECRET_KEY", "")
    if _is_placeholder(jwt_secret) or len(jwt_secret) < 32:
        findings.append(Finding("FAIL", "JWT_SECRET_KEY is missing, weak, or a placeholder"))
    else:
        findings.append(Finding("PASS", "JWT_SECRET_KEY meets the minimum length and placeholder checks"))

    database_password = env.get("POSTGRES_PASSWORD", "")
    if _is_placeholder(database_password):
        findings.append(Finding("FAIL", "POSTGRES_PASSWORD is missing or uses a default placeholder"))
    else:
        findings.append(Finding("PASS", "POSTGRES_PASSWORD is configured outside tracked files"))

    app_env = env.get("APP_ENV", "development").lower()
    database_url = env.get("DATABASE_URL_DOCKER" if app_env == "production" else "DATABASE_URL", "")
    if app_env == "production" and urlsplit(database_url).hostname in {
        None,
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        findings.append(Finding("FAIL", "production database URL does not use a container/network host"))
    elif database_url:
        findings.append(Finding("PASS", "database URL host matches the selected runtime profile"))

    if env.get("AI_ENABLED", "false").lower() == "true" and not env.get("DOUBAO_API_KEY"):
        findings.append(Finding("FAIL", "AI is enabled but DOUBAO_API_KEY is not configured"))
    elif env.get("DOUBAO_API_KEY"):
        findings.append(Finding("PASS", "AI key is configured outside tracked files"))
    else:
        findings.append(Finding("PASS", "AI is disabled and no API key is required"))

    origins = {item.strip() for item in env.get("CORS_ALLOWED_ORIGINS", "").split(",")}
    if "*" in origins:
        findings.append(Finding("FAIL", "CORS_ALLOWED_ORIGINS contains a wildcard"))
    else:
        findings.append(Finding("PASS", "CORS configuration contains no wildcard"))
    return findings


def main() -> int:
    findings = run_checks()
    for finding in findings:
        print(f"[{finding.level}] {finding.message}")
    return 1 if any(item.level == "FAIL" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
