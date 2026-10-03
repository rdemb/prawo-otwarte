"""Conservative publication checks. Reports paths/rules, never secret values."""
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PARTS = {".codex", ".agents", ".ssh", "data", "uploads", "backups", "private", ".venv"}
PRIVATE_NAMES = {"agents.md", "claude.md", "gemini.md", "copilot-instructions.md", ".env"}
PRIVATE_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".safetensors", ".gguf", ".p12", ".key"}
SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    re.compile(rb"\bsk-(?:proj-|svcacct-)[A-Za-z0-9_-]{30,}\b"),
]


def inspect(path, content):
    name = PurePosixPath(path)
    parts = {part.lower() for part in name.parts}
    findings = []
    if parts & PRIVATE_PARTS or name.name.lower() in PRIVATE_NAMES or name.suffix.lower() in PRIVATE_SUFFIXES:
        findings.append("private file category")
    if name.name.startswith(".env.") and name.name != ".env.example":
        findings.append("local environment configuration")
    if re.search(r"raport[-_]vps|codex.*prompt|prompt.*codex|code[x_].*migracj|^PO_\d+_(?:REPORT|PROGRESS|CODEX)",name.name,re.I):
        findings.append("private operations material")
    if any(pattern.search(content) for pattern in SECRET_PATTERNS):
        findings.append("credential pattern")
    return findings


def main():
    paths = subprocess.check_output(["git","ls-files","-z"],cwd=ROOT).decode().split("\0")
    failures = []
    for path in filter(None,paths):
        file = ROOT / path
        if file.is_file():
            failures.extend((path,rule) for rule in inspect(path,file.read_bytes()))
    for path,rule in failures:
        print(f"BLOCKED: {path}: {rule}")
    if failures:
        raise SystemExit(1)
    print("Public repository checks passed. This is a targeted check, not a complete security audit.")


if __name__ == "__main__":
    main()
