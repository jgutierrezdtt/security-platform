#!/usr/bin/env python3
"""
Onboarding masivo de repos existentes al security-platform.

Para cada repo de la organización (o de una lista), aplica los consumer templates:
  - .github/workflows/security.yml
  - .github/workflows/release.yml
  - .github/dependabot.yml
  - .github/PULL_REQUEST_TEMPLATE.md
  - .github/CODEOWNERS  (solo si no existe)
  - .semgrepignore

Crea un PR en cada repo con todos los cambios, listo para que el equipo revise.

Uso:
    # Onboarding de todos los repos de la org (excluye repos archivados y forks)
    python3 scripts/bulk-onboard.py --org amazing-protection

    # Solo repos específicos (de un fichero, uno por línea)
    python3 scripts/bulk-onboard.py --org amazing-protection --repos-file repos.txt

    # Simular sin crear PRs
    python3 scripts/bulk-onboard.py --org amazing-protection --dry-run

    # Forzar re-onboarding aunque ya tenga el workflow
    python3 scripts/bulk-onboard.py --org amazing-protection --force

    # Limitar para pruebas
    python3 scripts/bulk-onboard.py --org amazing-protection --limit 5

Requiere:
    GH_TOKEN con permisos: contents:write, pull-requests:write, metadata:read
    pip install requests

Variables de entorno opcionales:
    SECURITY_PLATFORM_REPO  (default: amazing-protection/security-platform)
    SECURITY_PLATFORM_REF   (default: main)
"""

import os
import sys
import json
import base64
import argparse
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ pip install requests")
    sys.exit(1)

# ── Configuración ─────────────────────────────────────────────────────────────

PLATFORM_REPO = os.environ.get("SECURITY_PLATFORM_REPO", "amazing-protection/security-platform")
PLATFORM_REF  = os.environ.get("SECURITY_PLATFORM_REF", "main")

# Templates a aplicar: (ruta en security-platform, ruta destino en el repo)
TEMPLATES = [
    ("templates/consumer/.github/workflows/security.yml",        ".github/workflows/security.yml"),
    ("templates/consumer/.github/workflows/release.yml",         ".github/workflows/release.yml"),
    ("templates/consumer/.github/dependabot.yml",                ".github/dependabot.yml"),
    ("templates/consumer/.github/PULL_REQUEST_TEMPLATE.md",      ".github/PULL_REQUEST_TEMPLATE.md"),
    ("templates/consumer/.semgrepignore",                        ".semgrepignore"),
]

# CODEOWNERS solo se añade si NO existe ya en el repo destino
CODEOWNERS_TEMPLATE = ("templates/consumer/.github/CODEOWNERS", ".github/CODEOWNERS")

PR_TITLE  = "security: onboarding al security-platform de amazing-protection"
PR_BRANCH = "security/onboarding-platform"
PR_BODY   = """\
## Onboarding al Security Platform

Este PR fue generado automáticamente por el script de onboarding masivo.

### Qué incluye

| Archivo | Propósito |
|---------|-----------|
| `.github/workflows/security.yml` | Pipeline de Semgrep + Dependabot (reusable) |
| `.github/workflows/release.yml` | Pipeline de build con SLSA Level 3 |
| `.github/dependabot.yml` | Actualizaciones automáticas de dependencias |
| `.github/PULL_REQUEST_TEMPLATE.md` | Template con checklist de seguridad |
| `.semgrepignore` | Patrones de archivos excluidos del análisis |

### Qué hacer

1. Revisar que los workflows llaman correctamente a tu tipo de proyecto
2. Ajustar el `build-command` en `release.yml` si aplica
3. Revisar `.github/dependabot.yml` y descomentar los ecosistemas que uses
4. Aprobar y mergear — los workflows se activarán en el próximo PR

### Documentación

📖 [Guía completa de onboarding](https://github.com/amazing-protection/security-platform/blob/main/ONBOARDING.md)

---
*Generado por [security-platform](https://github.com/amazing-protection/security-platform) · Script: `scripts/bulk-onboard.py`*
"""

# ── API Helper ────────────────────────────────────────────────────────────────

class GitHubAPI:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def get(self, path: str, **kwargs):
        resp = self.session.get(f"https://api.github.com{path}", timeout=30, **kwargs)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def get_paginated(self, path: str, **kwargs) -> list:
        results = []
        url = f"https://api.github.com{path}"
        params = kwargs.pop("params", {})
        params["per_page"] = 100
        while url:
            resp = self.session.get(url, params=params, timeout=30, **kwargs)
            resp.raise_for_status()
            results.extend(resp.json())
            url = resp.links.get("next", {}).get("url")
            params = {}  # solo en la primera request
        return results

    def post(self, path: str, **kwargs):
        resp = self.session.post(f"https://api.github.com{path}", timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def put(self, path: str, **kwargs):
        resp = self.session.put(f"https://api.github.com{path}", timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()


# ── Lógica principal ──────────────────────────────────────────────────────────

def get_template_content(api: GitHubAPI, template_path: str) -> str:
    """Obtiene el contenido de un template desde security-platform."""
    data = api.get(f"/repos/{PLATFORM_REPO}/contents/{template_path}", params={"ref": PLATFORM_REF})
    if not data:
        raise FileNotFoundError(f"Template no encontrado: {template_path}")
    # GitHub devuelve el contenido en base64
    return base64.b64decode(data["content"]).decode("utf-8")


def file_exists(api: GitHubAPI, repo: str, path: str, branch: str) -> tuple[bool, str | None]:
    """Comprueba si un archivo existe en el repo y devuelve (existe, sha)."""
    data = api.get(f"/repos/{repo}/contents/{path}", params={"ref": branch})
    if not data:
        return False, None
    return True, data.get("sha")


def get_default_branch(api: GitHubAPI, repo: str) -> str:
    data = api.get(f"/repos/{repo}")
    return data["default_branch"]


def create_or_update_branch(api: GitHubAPI, repo: str, branch: str, base_branch: str):
    """Crea la rama de onboarding si no existe."""
    ref_data = api.get(f"/repos/{repo}/git/ref/heads/{base_branch}")
    sha = ref_data["object"]["sha"]

    try:
        api.post(f"/repos/{repo}/git/refs", json={
            "ref": f"refs/heads/{branch}",
            "sha": sha,
        })
        print(f"    ✅ Rama '{branch}' creada")
    except requests.HTTPError as e:
        if e.response.status_code == 422:
            print(f"    ℹ️  Rama '{branch}' ya existe, reutilizando")
        else:
            raise


def commit_file(api: GitHubAPI, repo: str, path: str, content: str, branch: str, file_sha: str | None):
    """Crea o actualiza un archivo en el repo."""
    payload = {
        "message": f"ci: add {path} [security-platform onboarding]",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": branch,
    }
    if file_sha:
        payload["sha"] = file_sha

    api.put(f"/repos/{repo}/contents/{path}", json=payload)


def pr_exists(api: GitHubAPI, repo: str, branch: str) -> bool:
    prs = api.get(f"/repos/{repo}/pulls", params={"head": f"{repo.split('/')[0]}:{branch}", "state": "open"})
    return bool(prs)


def onboard_repo(api: GitHubAPI, repo: str, dry_run: bool, force: bool, templates_cache: dict) -> str:
    """
    Aplica los templates a un repo. Devuelve el estado:
    'skipped', 'pr_exists', 'done', 'error'
    """
    try:
        # Obtener rama por defecto
        default_branch = get_default_branch(api, repo)

        # Verificar si ya tiene el workflow de seguridad
        already_has_security, _ = file_exists(api, repo, ".github/workflows/security.yml", default_branch)
        if already_has_security and not force:
            return "skipped"

        # Verificar si ya hay un PR de onboarding abierto
        if pr_exists(api, repo, PR_BRANCH):
            return "pr_exists"

        if dry_run:
            return "dry_run"

        # Crear rama
        create_or_update_branch(api, repo, PR_BRANCH, default_branch)

        # Aplicar cada template
        for template_src, dest_path in TEMPLATES:
            content = templates_cache[template_src]
            _, existing_sha = file_exists(api, repo, dest_path, PR_BRANCH)
            commit_file(api, repo, dest_path, content, PR_BRANCH, existing_sha)
            print(f"    📄 {dest_path}")

        # CODEOWNERS solo si no existe
        codeowners_exists, _ = file_exists(api, repo, CODEOWNERS_TEMPLATE[1], PR_BRANCH)
        if not codeowners_exists:
            content = templates_cache[CODEOWNERS_TEMPLATE[0]]
            commit_file(api, repo, CODEOWNERS_TEMPLATE[1], content, PR_BRANCH, None)
            print(f"    📄 {CODEOWNERS_TEMPLATE[1]} (nuevo)")

        # Crear PR
        api.post(f"/repos/{repo}/pulls", json={
            "title": PR_TITLE,
            "head": PR_BRANCH,
            "base": default_branch,
            "body": PR_BODY,
            "draft": False,
        })

        return "done"

    except Exception as e:
        print(f"    ❌ Error: {e}")
        return "error"


def main():
    parser = argparse.ArgumentParser(description="Onboarding masivo de repos al security-platform")
    parser.add_argument("--org", required=True, help="Nombre de la organización de GitHub")
    parser.add_argument("--repos-file", help="Fichero con repos (uno por línea: org/repo)")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin crear PRs")
    parser.add_argument("--force", action="store_true", help="Re-onboarding aunque ya tengan el workflow")
    parser.add_argument("--limit", type=int, help="Limitar a N repos (para pruebas)")
    parser.add_argument("--exclude", nargs="*", default=[], help="Repos a excluir (nombre sin org)")
    args = parser.parse_args()

    token = os.environ.get("GH_TOKEN")
    if not token:
        print("❌ Falta GH_TOKEN")
        sys.exit(1)

    api = GitHubAPI(token)

    # Obtener lista de repos
    if args.repos_file:
        with open(args.repos_file) as f:
            repos = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        # Normalizar: si el usuario pone solo el nombre sin org, añadir la org
        repos = [r if "/" in r else f"{args.org}/{r}" for r in repos]
    else:
        print(f"🔍 Listando repos de {args.org}...")
        all_repos = api.get_paginated(f"/orgs/{args.org}/repos", params={"type": "all"})
        repos = [
            r["full_name"] for r in all_repos
            if not r["archived"]
            and not r["fork"]
            and r["name"] not in args.exclude
            # Excluir los repos del propio platform
            and r["name"] not in ["security-platform", "security-exceptions"]
        ]

    if args.limit:
        repos = repos[:args.limit]

    print(f"📦 {len(repos)} repos a procesar{' (DRY RUN)' if args.dry_run else ''}\n")

    # Pre-cargar todos los templates (para no repetir la llamada por cada repo)
    print("⬇️  Cargando templates desde security-platform...")
    templates_cache = {}
    all_templates = TEMPLATES + [CODEOWNERS_TEMPLATE]
    for src, _ in all_templates:
        if src not in templates_cache:
            templates_cache[src] = get_template_content(api, src)
    print("✅ Templates cargados\n")

    # Procesar repos
    results = {"done": [], "skipped": [], "pr_exists": [], "dry_run": [], "error": []}

    for i, repo in enumerate(repos, 1):
        print(f"[{i}/{len(repos)}] {repo}")
        status = onboard_repo(api, repo, args.dry_run, args.force, templates_cache)
        results[status].append(repo)
        print(f"    → {status}")

        # Evitar rate limiting
        if not args.dry_run and i % 10 == 0:
            time.sleep(2)

    # Resumen final
    print(f"\n{'='*60}")
    print(f"✅ PRs creados:         {len(results['done'])}")
    print(f"⏭️  Ya onboarded:        {len(results['skipped'])}")
    print(f"ℹ️  PR ya existía:       {len(results['pr_exists'])}")
    print(f"🔵 Dry run (sin PR):    {len(results['dry_run'])}")
    print(f"❌ Errores:             {len(results['error'])}")

    if results["error"]:
        print("\nRepos con error:")
        for r in results["error"]:
            print(f"  • {r}")

    # Actualizar monitored-repos.txt con los repos onboarded
    if results["done"] and not args.dry_run:
        monitored_path = Path("config/monitored-repos.txt")
        if monitored_path.exists():
            existing = set(monitored_path.read_text().splitlines())
            new_repos = [r for r in results["done"] if r not in existing]
            if new_repos:
                with open(monitored_path, "a") as f:
                    f.write("\n".join(new_repos) + "\n")
                print(f"\n📝 {len(new_repos)} repos añadidos a config/monitored-repos.txt")

    sys.exit(1 if results["error"] else 0)


if __name__ == "__main__":
    main()
