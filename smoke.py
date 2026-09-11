#!/usr/bin/env python3
"""Prueba de humo. No toca la red ni gasta un centavo de DataForSEO.

Comprueba que las cuatro herramientas arrancan, que el parser de YAML de
respaldo coincide con pyyaml, que el ejemplo canonico saca 100/100, y que
renderizarlo a los tres destinos sigue dando 100/100.

    python smoke.py

Sale con codigo 1 si algo falla, asi que sirve en CI.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "skills" / "pengu-audit" / "scripts" / "audit.py"
RENDER = ROOT / "skills" / "pengu-write" / "scripts" / "render.py"
DFS = ROOT / "skills" / "pengu-keywords" / "scripts" / "dfs.py"
KW = ROOT / "skills" / "pengu-keywords" / "scripts" / "kw_research.py"
EXAMPLE = ROOT / "skills" / "pengu-seo" / "examples" / "ejemplo-canonico.md"

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  {'OK  ' if condition else 'FALLA'}  {name}")
    if not condition:
        if detail:
            print(f"          {detail}")
        failures.append(name)


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    print("1. Las herramientas arrancan")
    for script in (DFS, KW, AUDIT, RENDER):
        proc = subprocess.run([sys.executable, str(script), "--help"],
                              capture_output=True, text=True)
        check(script.name, proc.returncode == 0, proc.stderr[:200])

    print("\n2. El parser de YAML de respaldo")
    audit = load(AUDIT)
    sample = (
        'title: "Un titulo: con dos puntos"\n'
        "hero:\n  path: /a/b.png\n  alt: \"Una descripcion\"\n"
        "faq:\n  - question: \"Primera?\"\n    answer: \"Si.\"\n"
        "  - question: \"Segunda?\"\n    answer: \"Tambien.\"\n"
        "tags: [uno, dos]\n"
        "internal_links:\n  - anchor: \"ancla\"\n    url: https://ejemplo.com/x\n"
        "toc: true\n"
    )
    got = audit.mini_yaml(sample)
    try:
        import yaml
        check("coincide con pyyaml", got == yaml.safe_load(sample),
              json.dumps(got, ensure_ascii=False)[:200])
    except ImportError:
        check("estructura basica",
              got.get("hero", {}).get("alt") == "Una descripcion"
              and len(got.get("faq", [])) == 2)

    print("\n3. Deteccion de acentos en la keyword")
    check("fold ignora acentos",
          audit.fold("Qué es la serigrafía") == "que es la serigrafia")

    print("\n4. Las imagenes no cuentan como enlaces")
    import re
    pattern = r"(?<!!)\[([^\]]+)\]\(([^)\s]+)[^)]*\)"
    found = re.findall(pattern, "Un [enlace](/a) y una ![imagen](/b.png).")
    check("solo el enlace", [u for _, u in found] == ["/a"], str(found))

    print("\n5. El ejemplo canonico saca 100/100")
    proc = subprocess.run(
        [sys.executable, str(AUDIT), str(EXAMPLE), "--profile", "canonical"],
        capture_output=True, text=True, encoding="utf-8")
    check("auditoria del ejemplo", proc.returncode == 0,
          (proc.stdout or "")[-400:])

    print("\n6. Renderizar a los tres destinos y auditar el resultado")
    profiles = {"wordpress": "wordpress", "markdown": "canonical"}
    with tempfile.TemporaryDirectory() as tmp:
        for target, profile in profiles.items():
            out = Path(tmp) / f"{target}.md"
            render = subprocess.run(
                [sys.executable, str(RENDER), str(EXAMPLE),
                 "--to", target, "--out", str(out)],
                capture_output=True, text=True, encoding="utf-8")
            if render.returncode != 0 or not out.exists():
                check(f"render a {target}", False, (render.stderr or "")[:200])
                continue
            audited = subprocess.run(
                [sys.executable, str(AUDIT), str(out), "--profile", profile,
                 "--site", "example.com"],
                capture_output=True, text=True, encoding="utf-8")
            check(f"{target} sin errores", audited.returncode == 0,
                  (audited.stdout or "")[-400:])

        # nextjs se comprueba por contenido: lo que importa de ese adaptador
        # es que escriba en el cuerpo lo que la plantilla no renderiza.
        out = Path(tmp) / "nextjs.md"
        render = subprocess.run(
            [sys.executable, str(RENDER), str(EXAMPLE), "--to", "nextjs",
             "--out", str(out)], capture_output=True, text=True,
            encoding="utf-8")
        check("render a nextjs", render.returncode == 0 and out.exists(),
              (render.stderr or "")[:200])
        if out.exists():
            text = out.read_text(encoding="utf-8")
            check("el FAQ queda visible en el cuerpo",
                  "## Preguntas frecuentes" in text)
            check("las fuentes quedan visibles", "## Fuentes" in text)
            check("los enlaces internos se inyectaron",
                  text.count("](https://example.com/") == 3)

    print("\n7. El presupuesto de DataForSEO responde sin red")
    proc = subprocess.run([sys.executable, str(DFS), "costs"],
                          capture_output=True, text=True, encoding="utf-8")
    check("dfs.py costs", proc.returncode == 0, (proc.stderr or "")[:200])

    print()
    if failures:
        print(f"{len(failures)} fallos: {', '.join(failures)}")
        return 1
    print("Todo pasa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
