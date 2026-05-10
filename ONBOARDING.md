# Guía de Incorporación al Sistema de Seguridad

> **Para equipos que quieren integrar sus repositorios con el sistema de seguridad de `amazing-protection`.**

---

## Checklist de incorporación (~2 horas)

### Paso 1: Configuración del repositorio en GitHub (15 min)

```bash
REPO="amazing-protection/tu-repo"

# 1. Habilitar GitHub Advanced Security
gh api repos/${REPO} -X PATCH \
  --field security_and_analysis='{"advanced_security":{"status":"enabled"},"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"}}'

# 2. Habilitar Dependabot
gh api repos/${REPO} -X PATCH \
  --field security_and_analysis='{"dependabot_security_updates":{"status":"enabled"}}'

# 3. Habilitar Code Scanning
gh api repos/${REPO}/code-scanning/default-setup -X PATCH \
  --field state=configured --field query_suite=security-extended
```

### Paso 2: Copiar templates (10 min)

```bash
# Clonar tu repo
git clone https://github.com/amazing-protection/tu-repo.git
cd tu-repo

# Descargar los templates
BASE="https://raw.githubusercontent.com/amazing-protection/security-platform/main/templates/consumer"

# Crear estructura de directorios
mkdir -p .github/workflows config/semgrep

# Descargar cada template
curl -sfL "${BASE}/.github/workflows/security.yml" -o .github/workflows/security.yml
curl -sfL "${BASE}/.github/workflows/release.yml" -o .github/workflows/release.yml
curl -sfL "${BASE}/.github/dependabot.yml" -o .github/dependabot.yml
curl -sfL "${BASE}/.github/CODEOWNERS" -o .github/CODEOWNERS
curl -sfL "${BASE}/.github/PULL_REQUEST_TEMPLATE.md" -o .github/PULL_REQUEST_TEMPLATE.md
curl -sfL "${BASE}/.semgrepignore" -o .semgrepignore

echo "✅ Templates descargados"
```

### Paso 3: Personalizar los templates (20 min)

**`.github/workflows/security.yml`**: Ajustar `semgrep-rules` según tu stack.

**`.github/CODEOWNERS`**: Reemplazar `@amazing-protection/developers` por el team de tu equipo.

**`.github/dependabot.yml`**: Descomentar los ecosistemas que usas (npm, pip, go, etc.).

### Paso 4: Configurar secrets (15 min)

```bash
# 1. Crear EXCEPTIONS_READER_TOKEN
# Ve a: github.com/settings/personal-access-tokens/new
# - Fine-grained token
# - Resource owner: amazing-protection
# - Repository: Only security-exceptions
# - Permission: Contents: Read-only
# - Expiry: 1 año
#
# Luego:
gh secret set EXCEPTIONS_READER_TOKEN --repo amazing-protection/tu-repo

# 2. Crear DEPENDABOT_CHECK_TOKEN
# Ve a: github.com/settings/personal-access-tokens/new
# - Fine-grained token
# - Resource owner: amazing-protection
# - Repository: Only tu-repo
# - Permission: Dependabot alerts: Read-only
# - Expiry: 1 año
gh secret set DEPENDABOT_CHECK_TOKEN --repo amazing-protection/tu-repo

# 3. Opcional: SEMGREP_APP_TOKEN (para Semgrep Cloud Platform)
gh secret set SEMGREP_APP_TOKEN --repo amazing-protection/tu-repo
```

### Paso 5: Configurar Branch Protection (20 min)

```bash
REPO="amazing-protection/tu-repo"

# Crear Ruleset para main
gh api repos/${REPO}/rulesets -X POST --input - << 'EOF'
{
  "name": "security-gate",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": true,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          {"context": "Semgrep SAST"},
          {"context": "Dependabot Status"}
        ]
      }
    }
  ]
}
EOF
```

### Paso 6: Primer commit y validación (15 min)

```bash
# Añadir archivos al repo
git add .github/ .semgrepignore
git commit -m "ci: add security gate with Semgrep and Dependabot"
git push origin main

# Crear un PR de prueba para verificar que todo funciona
git checkout -b test/security-integration
echo "# Security Test" >> SECURITY-TEST.md
git add SECURITY-TEST.md
git commit -m "test: verify security gate"
git push origin test/security-integration

gh pr create --title "test: verify security gate" --body "Testing security integration"
```

### Paso 7: Añadir el repo al dashboard de seguridad (5 min)

```bash
# Abrir un PR en security-platform para añadir tu repo al monitoring
echo "amazing-protection/tu-repo" >> /tmp/repo-entry.txt

# Enviar PR al security-platform
gh pr create \
  --repo amazing-protection/security-platform \
  --title "feat: add tu-repo to security monitoring" \
  --body "Añadir amazing-protection/tu-repo al dashboard de seguridad."
```

---

## Verificación de la integración

```bash
# Verificar que los workflows existen
gh workflow list --repo amazing-protection/tu-repo

# Verificar que los secrets están configurados
gh secret list --repo amazing-protection/tu-repo

# Verificar el estado de GHAS
gh api repos/amazing-protection/tu-repo --jq '.security_and_analysis'

# Ver el último run del security workflow
gh run list --repo amazing-protection/tu-repo --workflow security.yml --limit 5
```

---

## ¿Problemas frecuentes?

| Problema | Solución |
|----------|----------|
| "EXCEPTIONS_READER_TOKEN has insufficient permissions" | Verificar que el PAT tiene `Contents: Read-only` en `security-exceptions` |
| "Dependabot Status" check no aparece como required | Hacer al menos 1 run del workflow antes de configurarlo como required |
| Semgrep falla con "No rules found" | Verificar que `semgrep-rules` tiene al menos `p/default` |
| Code Scanning no recibe el SARIF | Habilitar GHAS en el repositorio |

---

## Contacto y soporte

- **Documentación completa**: [security-platform/docs/tutorials](https://github.com/amazing-protection/security-platform/tree/main/docs/tutorials)
- **Solicitar excepción**: [Issue en security-platform](https://github.com/amazing-protection/security-platform/issues/new?template=exception-request.yml)
- **Security team**: @amazing-protection/security-team
