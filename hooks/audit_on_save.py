#!/usr/bin/env python3
"""Hook PostToolUse de Claude Code: audita un post en cuanto se guarda.

Una regla escrita se incumple en silencio; una que corre al guardar, no. Claude
Code llama a este script despues de cada Edit o Write con un JSON por stdin
que trae la ruta del archivo. Si es un .md con frontmatter y hay un
pengu-seo.json hacia arriba, corre audit.py sobre ese archivo.

Codigos de salida, segun el contrato de hooks de Claude Code:

  0   no aplica, o el post pasa (los avisos se muestran pero no cortan)
  2   hay errores; el informe va por stderr y Claude lo ve para corregirlo

Nunca lanza: un hook que falla por un motivo propio no debe bloquear una
edicion que no tiene nada que ver con SEO.

Instalacion manual, sin plugin, en ~/.claude/settings.json:

  {"hooks": {"PostToolUse": [{"matcher": "Edit|Write", "hooks": [
     {"type": "command",
      "command": "python \"C:/ruta/seo-preflight/hooks/audit_on_save.py\""}]}]}}
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CONFIG_NAME = "pengu-seo.json"
AUDIT = Path(__file__).resolve().parent.parent / "skills" / "pengu-audit" / "scripts" / "audit.py"


def file_from_stdin() -> str | None:
    if len(sys.argv) > 1:
        return sys.argv[1]
    try:
        raw = sys.stdin.read()
    except OSError:
        return None
    if not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    tool_input = data.get("tool_input") or {}
    return tool_input.get("file_path") or tool_input.get("path")


def find_config(start: Path) -> Path | None:
    here = start if start.is_dir() else start.parent
    for folder in [here, *here.parents]:
        candidate = folder / CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    target = file_from_stdin()
    if not target:
        return 0
    path = Path(target)
    if path.suffix.lower() != ".md" or not path.is_file():
        return 0
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:4]
    except OSError:
        return 0
    if not head.startswith("---"):
        return 0  # un README o una nota, no un post
    config = find_config(path.resolve())
    if not config or not AUDIT.is_file():
        return 0
    try:
        proc = subprocess.run(
            [sys.executable, str(AUDIT), str(path), "--config", str(config)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60)
    except (OSError, subprocess.SubprocessError):
        return 0
    report = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0:
        if "WARN" in report:
            print(report)
        return 0
    sys.stderr.write("pengu-audit: el post tiene errores. Corregilos antes de seguir.\n\n")
    sys.stderr.write(report)
    return 2


if __name__ == "__main__":
    sys.exit(main())
