#!/usr/bin/env python3
"""
Genera el dashboard de seguridad de la organización.
Actualiza el README.md con métricas actualizadas de todos los repos monitorizados.

Uso:
    python3 scripts/generate-org-report.py \
        --repos-file config/monitored-repos.txt \
        --output .security/dashboard.json \
        --readme README.md

Requiere:
    GH_TOKEN con permisos: security_events:read, contents:read
"""

import json
import os
import sys
import argparse
import re
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("❌ pip install requests")
    sys.exit(1)


def gh_api(path: str, token: str, params: dict = None) -> dict | list | None:
    """Wrapper para la API de GitHub con manejo de errores."""
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = requests.get(url, headers=headers, params=params, timeout=30)

    if resp.status_code == 403:
        print(f"  ⚠️  Sin permisos para {path}")
        return None
    if resp.status_code == 404:
        print(f"  ⚠️  No encontrado: {path}")
        return None
    if resp.status_code != 200:
        print(f"  ❌ Error {resp.status_code}: {path}")
        return None

    return resp.json()


def get_dependabot_stats(repo: str, token: str) -> dict:
    """Obtiene las estadísticas de Dependabot de un repo."""
    alerts = gh_api(f"/repos/{repo}/dependabot/alerts", token, params={"state": "open", "per_page": 100})

    if alerts is None:
        return {"enabled": False, "critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}

    counts = {"enabled": True, "critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}
    for alert in alerts:
        severity = alert.get("security_vulnerability", {}).get("severity", "unknown").lower()
        counts["total"] += 1
        if severity in counts:
            counts[severity] += 1

    return counts


def get_semgrep_stats(repo: str, token: str) -> dict:
    """Obtiene las estadísticas de Code Scanning (Semgrep/SARIF) de un repo."""
    alerts = gh_api(
        f"/repos/{repo}/code-scanning/alerts",
        token,
        params={"state": "open", "tool_name": "Semgrep", "per_page": 100},
    )

    if alerts is None:
        return {"enabled": False, "critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}

    counts = {"enabled": True, "critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}
    for alert in alerts:
        severity = alert.get("rule", {}).get("severity", "unknown").lower()
        counts["total"] += 1
        if severity in counts:
            counts[severity] += 1

    return counts


def get_secret_scanning_stats(repo: str, token: str) -> dict:
    """Obtiene el número de alertas activas de Secret Scanning."""
    alerts = gh_api(
        f"/repos/{repo}/secret-scanning/alerts",
        token,
        params={"state": "open", "per_page": 100},
    )

    if alerts is None:
        return {"enabled": False, "total": 0}

    return {"enabled": True, "total": len(alerts)}


def severity_emoji(critical: int, high: int) -> str:
    if critical > 0:
        return "🔴"
    if high > 0:
        return "🟠"
    return "🟢"


def generate_markdown_table(repo_stats: list) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"*Actualizado: {now} · [Ver workflow](.github/workflows/org-security-report.yml)*\n",
        "| Repositorio | Estado | Semgrep | Dependabot | Secret Scanning |",
        "|-------------|--------|---------|------------|-----------------|",
    ]

    for s in repo_stats:
        repo_link = f"[{s['repo'].split('/')[-1]}](https://github.com/{s['repo']})"

        semgrep = s["semgrep"]
        dep = s["dependabot"]
        sec = s["secret_scanning"]

        sem_icon = severity_emoji(semgrep["critical"], semgrep["high"])
        dep_icon = severity_emoji(dep["critical"], dep["high"])

        semgrep_cell = f"{sem_icon} C:{semgrep['critical']} H:{semgrep['high']}" if semgrep["enabled"] else "⚫ N/A"
        dep_cell = f"{dep_icon} C:{dep['critical']} H:{dep['high']}" if dep["enabled"] else "⚫ N/A"
        sec_cell = f"{'⚠️' if sec['total'] > 0 else '✅'} {sec['total']}" if sec["enabled"] else "⚫ N/A"

        overall = "✅" if all([semgrep["enabled"], dep["enabled"]]) else "⚠️"

        lines.append(f"| {repo_link} | {overall} | {semgrep_cell} | {dep_cell} | {sec_cell} |")

    return "\n".join(lines)


def update_readme(readme_path: str, dashboard_content: str) -> bool:
    """Reemplaza el contenido entre marcadores en el README."""
    start_marker = "<!-- SECURITY_DASHBOARD_START -->"
    end_marker = "<!-- SECURITY_DASHBOARD_END -->"

    with open(readme_path) as f:
        content = f.read()

    if start_marker not in content or end_marker not in content:
        print(f"❌ Marcadores no encontrados en {readme_path}")
        return False

    pattern = re.compile(
        re.escape(start_marker) + r".*?" + re.escape(end_marker),
        re.DOTALL,
    )
    new_content = pattern.sub(
        f"{start_marker}\n\n{dashboard_content}\n\n{end_marker}",
        content,
    )

    with open(readme_path, "w") as f:
        f.write(new_content)

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos-file", required=True)
    parser.add_argument("--output", default=".security/dashboard.json")
    parser.add_argument("--readme", default="README.md")
    args = parser.parse_args()

    token = os.environ.get("GH_TOKEN")
    if not token:
        print("❌ Falta GH_TOKEN")
        sys.exit(1)

    # Leer lista de repos
    repos = []
    with open(args.repos_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                repos.append(line)

    if not repos:
        print("⚠️  No hay repos en el archivo de monitorización")
        sys.exit(0)

    print(f"📊 Generando reporte para {len(repos)} repos...\n")

    repo_stats = []
    for repo in repos:
        print(f"→ {repo}")
        stats = {
            "repo": repo,
            "semgrep": get_semgrep_stats(repo, token),
            "dependabot": get_dependabot_stats(repo, token),
            "secret_scanning": get_secret_scanning_stats(repo, token),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        repo_stats.append(stats)

    # Guardar JSON raw
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(repo_stats, f, indent=2)
    print(f"\n💾 Dashboard guardado en {args.output}")

    # Actualizar README
    dashboard_md = generate_markdown_table(repo_stats)
    if update_readme(args.readme, dashboard_md):
        print(f"✅ README.md actualizado")
    else:
        print(f"⚠️  README.md no actualizado (sin marcadores)")

    # Resumen
    total_critical = sum(s["semgrep"]["critical"] + s["dependabot"]["critical"] for s in repo_stats)
    total_high = sum(s["semgrep"]["high"] + s["dependabot"]["high"] for s in repo_stats)
    print(f"\n📋 Resumen: {len(repos)} repos · 🔴 Critical: {total_critical} · 🟠 High: {total_high}")

    if total_critical > 0:
        print("❌ Hay vulnerabilidades CRITICAL — revisar inmediatamente")
        sys.exit(1)


if __name__ == "__main__":
    main()
