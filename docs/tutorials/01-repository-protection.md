# Tutorial 01 — Protección de Repositorios

> **Audiencia**: Administradores de repositorios y responsables de seguridad  
> **Nivel**: Intermedio  
> **Tiempo estimado**: 45 minutos  
> **Prerrequisitos**: Acceso de administrador al repositorio y a la organización

---

## ¿Qué cubre este tutorial?

La protección de un repositorio va mucho más allá de la visibilidad pública/privada. Este tutorial cubre la configuración completa de GitHub Advanced Security (GHAS) y todas las características de seguridad disponibles a nivel de repositorio.

---

## 1. Visibilidad y acceso al repositorio

### 1.1 Configuración de visibilidad

```bash
# Verificar visibilidad actual
gh repo view amazing-protection/mi-repo --json visibility -q '.visibility'

# Cambiar a privado (acción irreversible sin confirmación)
gh repo edit amazing-protection/mi-repo --visibility private
```

> **Regla organizacional**: En `amazing-protection`, todos los repositorios son **privados** por defecto. Solo se crean repos públicos con aprobación explícita del CISO.

### 1.2 Configurar como repositorio de plantilla (si aplica)

```bash
gh repo edit amazing-protection/mi-repo --template
```

---

## 2. GitHub Advanced Security (GHAS)

GHAS es el paraguas de características de seguridad de GitHub. Para repositorios privados requiere licencia. Para repos públicos, es gratuito.

### 2.1 Habilitar GHAS vía API

```bash
# Habilitar GHAS en el repositorio
gh api repos/amazing-protection/mi-repo \
  -X PATCH \
  --field security_and_analysis='{"advanced_security":{"status":"enabled"}}'
```

### 2.2 Verificar estado de GHAS

```bash
gh api repos/amazing-protection/mi-repo \
  --jq '.security_and_analysis'
```

La respuesta debe mostrar:
```json
{
  "advanced_security": { "status": "enabled" },
  "secret_scanning": { "status": "enabled" },
  "secret_scanning_push_protection": { "status": "enabled" },
  "dependabot_security_updates": { "status": "enabled" }
}
```

---

## 3. Secret Scanning

El secret scanning detecta secretos (tokens, claves API, contraseñas) que hayan sido comprometidos en el código fuente.

### 3.1 Habilitar secret scanning

```bash
gh api repos/amazing-protection/mi-repo \
  -X PATCH \
  --field security_and_analysis='{"secret_scanning":{"status":"enabled"}}'
```

### 3.2 Habilitar Push Protection

Push Protection **bloquea el push** si detecta un secreto conocido. Es la característica más valiosa porque previene el problema antes de que ocurra.

```bash
gh api repos/amazing-protection/mi-repo \
  -X PATCH \
  --field security_and_analysis='{"secret_scanning_push_protection":{"status":"enabled"}}'
```

### 3.3 Verificar alertas de secret scanning

```bash
# Listar todas las alertas abiertas
gh api repos/amazing-protection/mi-repo/secret-scanning/alerts \
  --jq '.[] | {number:.number, secret_type:.secret_type, state:.state}'
```

### 3.4 Configurar exclusiones personalizadas

Si hay archivos de test que contienen secretos falsos (fixtures), puedes excluirlos:

```yaml
# .github/secret_scanning.yml
paths-ignore:
  - "tests/fixtures/**"
  - "**/*.example"
  - "**/*.sample"
```

> ⚠️ **Nunca** excluyas directorios de producción. Las exclusiones son solo para archivos de test con datos falsos documentados.

---

## 4. Code Scanning (análisis estático)

Code Scanning integra herramientas SAST directamente en GitHub. Los resultados aparecen en el Security tab.

### 4.1 Habilitar CodeQL (herramienta oficial de GitHub)

```bash
# Configurar CodeQL con el conjunto de consultas de seguridad extendido
gh api repos/amazing-protection/mi-repo/code-scanning/default-setup \
  -X PATCH \
  --field state=configured \
  --field query_suite=security-extended \
  --field languages='["javascript","python","java"]'
```

### 4.2 Habilitar Semgrep (este repositorio)

El pipeline de Semgrep se configura a través del workflow reutilizable. Ver [Tutorial 07](07-semgrep-activation.md).

### 4.3 Gestionar alertas de Code Scanning

```bash
# Listar alertas abiertas
gh api repos/amazing-protection/mi-repo/code-scanning/alerts \
  --jq '.[] | {number:.number, rule_id:.rule.id, severity:.rule.severity}'

# Descartar una alerta como falso positivo
gh api repos/amazing-protection/mi-repo/code-scanning/alerts/123 \
  -X PATCH \
  --field state=dismissed \
  --field dismissed_reason=false_positive \
  --field dismissed_comment="Analizado por el equipo: el input está sanitizado en el middleware"
```

---

## 5. Configuración de seguridad a nivel de organización

Para mantener consistencia en todos los repositorios de `amazing-protection`:

### 5.1 Habilitar GHAS en toda la organización

```bash
# Habilitar para todos los repos de la organización
gh api orgs/amazing-protection/settings/security_products \
  -X POST \
  --field query_suite=security-extended \
  --field configuration='{
    "advanced_security": "enabled",
    "secret_scanning": "enabled",
    "secret_scanning_push_protection": "enabled",
    "dependabot_alerts": "enabled",
    "dependabot_security_updates": "enabled",
    "dependabot_version_updates": "enabled"
  }'
```

### 5.2 Políticas de seguridad organizacionales

En **Settings > Security** de la organización:

| Configuración | Valor recomendado |
|---------------|-------------------|
| **Dependabot alerts** | ✅ Habilitado para todos los repos |
| **Dependabot security updates** | ✅ Habilitado para todos los repos |
| **Secret scanning** | ✅ Habilitado para todos los repos |
| **Push protection** | ✅ Habilitado para todos los repos |
| **Private vulnerability reporting** | ✅ Habilitado |

---

## 6. Private Vulnerability Reporting (PVR)

PVR permite a investigadores de seguridad reportar vulnerabilidades de forma privada sin crear issues públicos.

```bash
# Habilitar PVR
gh api repos/amazing-protection/mi-repo \
  -X PATCH \
  --field private_vulnerability_reporting_enabled=true
```

Una vez habilitado, crea un archivo `SECURITY.md` explicando el proceso:

```markdown
# Security Policy

## Reporting a Vulnerability

Please use GitHub's private vulnerability reporting feature to report security issues.
Do NOT open public issues for security vulnerabilities.

[Report a vulnerability](https://github.com/amazing-protection/mi-repo/security/advisories/new)
```

---

## 7. Checklist de protección de repositorio

Ejecuta este script para verificar el estado de un repositorio:

```bash
#!/usr/bin/env bash
REPO="${1:-amazing-protection/mi-repo}"

echo "=== Security Status: ${REPO} ==="

gh api "repos/${REPO}" --jq '
  "Visibility: " + .visibility,
  "GHAS: " + (.security_and_analysis.advanced_security.status // "N/A"),
  "Secret Scanning: " + (.security_and_analysis.secret_scanning.status // "N/A"),
  "Push Protection: " + (.security_and_analysis.secret_scanning_push_protection.status // "N/A"),
  "Dependabot Alerts: " + (if .security_and_analysis.dependabot_security_updates.status != null then .security_and_analysis.dependabot_security_updates.status else "check_separately" end)
'

# Verificar alertas abiertas
ALERTS=$(gh api "repos/${REPO}/code-scanning/alerts?state=open" --jq 'length' 2>/dev/null || echo "N/A")
echo "Code Scanning Alerts (open): ${ALERTS}"

SECRET_ALERTS=$(gh api "repos/${REPO}/secret-scanning/alerts?state=open" --jq 'length' 2>/dev/null || echo "N/A")
echo "Secret Scanning Alerts (open): ${SECRET_ALERTS}"
```

### Checklist completo

- [ ] Repositorio configurado como **privado**
- [ ] **GHAS** habilitado
- [ ] **Secret Scanning** habilitado
- [ ] **Push Protection** habilitado
- [ ] **CodeQL** o Semgrep configurado y funcionando
- [ ] **Dependabot** habilitado (ver Tutorial 06)
- [ ] **Branch Protection** configurado en `main` (ver Tutorial 02)
- [ ] **CODEOWNERS** definido (ver Tutorial 04)
- [ ] **SECURITY.md** presente y actualizado
- [ ] **Private Vulnerability Reporting** habilitado
- [ ] **.github/secret_scanning.yml** configurado si hay fixtures de test

---

## Siguiente paso

➡️ [Tutorial 02 — Protección de Ramas](02-branch-protection.md)
