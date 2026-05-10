# Tutorial 07 — Activación de Semgrep

> **Audiencia**: DevSecOps engineers, desarrolladores  
> **Nivel**: Intermedio  
> **Tiempo estimado**: 60 minutos

---

## ¿Qué es Semgrep y por qué?

Semgrep es una herramienta de análisis estático (SAST) que detecta vulnerabilidades en el código fuente mediante reglas expresadas como patrones de código. A diferencia de otras herramientas de SAST, Semgrep:

- ✅ Entiende el **semantics del código** (no solo texto)
- ✅ Permite escribir **reglas personalizadas** fácilmente
- ✅ Genera **muy pocos falsos positivos** con las reglas adecuadas
- ✅ Funciona en múltiples lenguajes con la misma sintaxis
- ✅ Es **incremental**: analiza solo lo que cambió en un PR

**Comparativa con alternativas:**

| Herramienta | Tipo | OWASP | Custom rules | FP rate | Velocidad |
|------------|------|-------|-------------|---------|-----------|
| **Semgrep** | SAST | ✅ | ✅ Muy fácil | Bajo | Rápido |
| CodeQL | SAST | ✅ | Complejo | Bajo | Lento |
| SonarQube | SAST + Quality | ✅ | Sí | Medio | Medio |
| Snyk Code | SAST | ✅ | Limitado | Bajo | Rápido |

---

## 1. Integración básica — Llamar al workflow reutilizable

### 1.1 Configuración mínima

```yaml
# .github/workflows/security.yml en tu repositorio
name: Security Scan

on:
  push:
    branches: [main, "feature/**"]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 2 * * 1"  # Lunes 02:00 UTC

permissions:
  contents: read

jobs:
  semgrep:
    name: Semgrep SAST
    uses: amazing-protection/security-platform/.github/workflows/reusable/semgrep-scan.yml@main
    with:
      scan-scope: ${{ github.event_name == 'pull_request' && 'diff' || 'full' }}
      fail-on-severity: high
      upload-sarif: true
    secrets:
      SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}
      EXCEPTIONS_READER_TOKEN: ${{ secrets.EXCEPTIONS_READER_TOKEN }}
```

### 1.2 Configuración avanzada con todos los parámetros

```yaml
jobs:
  semgrep:
    uses: amazing-protection/security-platform/.github/workflows/reusable/semgrep-scan.yml@main
    with:
      scan-scope: diff                  # Solo cambios del PR (más rápido)
      fail-on-severity: high            # Bloquear en críticas y altas
      upload-sarif: true                # Subir al Security tab de GitHub
      create-issues: false              # No crear issues automáticamente
      exceptions-repo: amazing-protection/security-exceptions
      semgrep-rules: >-
        p/default
        p/security-audit
        p/owasp-top-ten
        p/nodejs
      report-only: false               # Bloquear pipeline si hay hallazgos
    secrets:
      SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}
      EXCEPTIONS_READER_TOKEN: ${{ secrets.EXCEPTIONS_READER_TOKEN }}
```

---

## 2. Configuración del repositorio para Semgrep

### 2.1 Archivo `.semgrepignore`

```
# config/semgrep/.semgrepignore o .semgrepignore en la raíz
#
# Patrones de archivos que Semgrep debe ignorar
# (fixtures de tests, código generado, dependencias)

# Dependencias y vendored code
node_modules/
vendor/
.venv/
__pycache__/
dist/
build/
target/

# Código generado automáticamente
*_generated.go
*_pb2.py
*_pb.js
*.min.js
*.min.css

# Tests y fixtures (datos de prueba)
tests/fixtures/
test/data/
**/__tests__/
**/*.test.js
**/*.spec.js
**/*.test.ts
**/*.spec.ts

# Documentación y ejemplos
docs/
examples/
*.example
*.sample

# Archivos de configuración de infraestructura (IaC tiene reglas propias)
terraform/
*.tf

# Archivos de migración de base de datos
migrations/
db/migrate/
```

### 2.2 Reglas personalizadas de la organización

```yaml
# config/semgrep/rules.yml
rules:
  # ─── Secretos y credenciales ──────────────────────
  - id: no-hardcoded-api-keys
    patterns:
      - pattern: |
          $KEY = "..."
      - metavariable-regex:
          metavariable: $KEY
          regex: '(?i)(api_key|apikey|api-key|secret|password|passwd|token|auth)'
      - metavariable-regex:
          metavariable: "\"...\""
          regex: '.{16,}'
    message: |
      Posible credencial hardcodeada en '$KEY'.
      Usa variables de entorno o un gestor de secretos (Azure Key Vault, AWS Secrets Manager).
    languages: [python, javascript, typescript, java, go]
    severity: ERROR
    metadata:
      category: security
      cwe: "CWE-798: Use of Hard-coded Credentials"
      owasp: "A07:2021 - Identification and Authentication Failures"

  # ─── SQL Injection ────────────────────────────────
  - id: sql-injection-string-concat
    patterns:
      - pattern: |
          $DB.query("..." + $USER_INPUT)
      - pattern: |
          $DB.execute(f"...{$USER_INPUT}...")
    message: |
      Posible SQL injection: concatenación directa de input en query SQL.
      Usa consultas parametrizadas: db.query("SELECT * FROM users WHERE id = ?", [userId])
    languages: [javascript, python]
    severity: ERROR
    metadata:
      category: security
      cwe: "CWE-89: SQL Injection"
      owasp: "A03:2021 - Injection"

  # ─── Configuraciones inseguras ────────────────────
  - id: debug-mode-production
    patterns:
      - pattern: |
          DEBUG = True
      - pattern: |
          debug: true
    paths:
      include:
        - "*.py"
        - "*.yml"
        - "*.yaml"
      exclude:
        - "tests/**"
        - "**/*.test.*"
        - "**/.env.example"
    message: |
      DEBUG mode habilitado. Asegúrate de que esto no llegue a producción.
      Usa variables de entorno: DEBUG = os.getenv('DEBUG', 'false') == 'true'
    languages: [python, yaml]
    severity: WARNING

  # ─── Logging de datos sensibles ───────────────────
  - id: no-log-sensitive-data
    patterns:
      - pattern: |
          console.log(..., $PASS, ...)
      - metavariable-regex:
          metavariable: $PASS
          regex: '(?i)(password|passwd|secret|token|credit_card|ssn|cvv)'
    message: |
      Posible logging de datos sensibles ($PASS).
      Nunca registres contraseñas, tokens o datos de tarjetas en logs.
    languages: [javascript, typescript]
    severity: WARNING
    metadata:
      category: security
      cwe: "CWE-532: Insertion of Sensitive Information into Log File"
```

---

## 3. Semgrep Cloud Platform (opcional pero recomendado)

La versión cloud de Semgrep ofrece:
- Dashboard web con histórico de hallazgos
- Gestión de reglas centralizada
- Análisis de PR en la UI de GitHub
- Métricas y tendencias

### 3.1 Obtener el token

1. Accede a [semgrep.dev](https://semgrep.dev) y crea una cuenta de organización
2. Ve a **Settings** → **API Tokens**
3. Crea un token con permisos `Agent (CI) Token`
4. Añade el token como secret: `gh secret set SEMGREP_APP_TOKEN --repo amazing-protection/mi-repo`

### 3.2 Configurar reglas en la plataforma

En el portal de Semgrep Cloud:
1. **Policies** → Seleccionar reglas para tu organización
2. Activa los conjuntos:
   - `p/default` — Conjunto curado de reglas de alta confianza
   - `p/owasp-top-ten` — Reglas del OWASP Top 10
   - `p/security-audit` — Auditoría de seguridad completa
   - Reglas específicas del lenguaje: `p/nodejs`, `p/python`, `p/java`

### 3.3 Gestión de reglas en repo privado (sin Cloud Platform)

Si no usas la plataforma cloud, gestiona las reglas en el repositorio `security-platform`:

```
config/semgrep/
├── rules.yml          ← Reglas personalizadas de la organización
├── .semgrepignore     ← Patrones de exclusión
└── rulesets/
    ├── critical.yml   ← Reglas que siempre bloquean
    ├── high.yml       ← Reglas de alta severidad
    └── audit.yml      ← Reglas informativas
```

Los repos consumidores apuntan a estas reglas remotas:

```bash
# Ejecutar con reglas del repositorio central
semgrep scan \
  --config https://raw.githubusercontent.com/amazing-protection/security-platform/main/config/semgrep/rules.yml \
  .
```

---

## 4. Ver resultados en el Security tab de GitHub

Cuando el workflow sube el SARIF, los resultados aparecen en:

```
Repositorio → Security → Code scanning alerts
```

**Gestionar alertas de Code Scanning:**

```bash
# Ver todas las alertas abiertas
gh api repos/amazing-protection/mi-repo/code-scanning/alerts?state=open \
  --jq '.[] | {number:.number, rule:.rule.id, severity:.rule.security_severity_level, file:.most_recent_instance.location.path}'

# Descartar una alerta como falso positivo
gh api repos/amazing-protection/mi-repo/code-scanning/alerts/42 \
  -X PATCH \
  --field state=dismissed \
  --field dismissed_reason=false_positive \
  --field dismissed_comment="El input está sanitizado antes de llegar a este punto"
```

---

## 5. Tabla de resultados en Pull Requests

El workflow reutilizable genera automáticamente una tabla en el PR. Ejemplo de salida:

```
## 🔍 Semgrep Security Scan — Resultados

**Repositorio**: `amazing-protection/mi-repo` | **Rama**: `feature/login` | **Commit**: `a1b2c3d4`

### Estado: 🟠 BLOQUEADO — Vulnerabilidades Altas

### 📊 Resumen

| 🔴 Críticas | 🟠 Altas | 🟡 Medias | 🔵 Bajas | ⚪ Info | ✅ Exceptuadas |
|:-----------:|:--------:|:---------:|:--------:|:-------:|:-------------:|
| **0**       | **2**    | 3         | 1        | 0       | 1             |

### 🚨 Hallazgos Activos

| # | Severidad   | Regla                    | Archivo              | Línea | Descripción                              |
|---|-------------|--------------------------|----------------------|-------|------------------------------------------|
| 1 | 🟠 HIGH     | `sql-injection`          | `src/db/queries.js`  | 45    | SQL injection via string concatenation…  |
| 2 | 🟠 HIGH     | `no-hardcoded-api-keys`  | `config/settings.py` | 12    | Posible credencial hardcodeada en API_K… |
```

---

## 6. Checklist

- [ ] Secret `SEMGREP_APP_TOKEN` configurado (si se usa Semgrep Cloud)
- [ ] Secret `EXCEPTIONS_READER_TOKEN` configurado
- [ ] Workflow de seguridad creado en el repositorio consumer
- [ ] `.semgrepignore` creado para excluir tests y código generado
- [ ] Code Scanning habilitado en el repositorio (para ver SARIF)
- [ ] Status check `Semgrep SAST` añadido como required en branch protection
- [ ] Revisión de los primeros resultados y validación de reglas

---

## Siguiente paso

➡️ [Tutorial 08 — Gestión de Excepciones](08-exception-management.md)
