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
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable/semgrep-scan.yml@main
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
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable/semgrep-scan.yml@main
    with:
      scan-scope: diff                  # Solo cambios del PR (más rápido)
      fail-on-severity: high            # Bloquear en críticas y altas
      upload-sarif: true                # Subir al Security tab de GitHub
      create-issues: false              # No crear issues automáticamente
      exceptions-repo: jgutierrezdtt/security-exceptions
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
4. Añade el token como secret: `gh secret set SEMGREP_APP_TOKEN --repo jgutierrezdtt/mi-repo`

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
  --config https://raw.githubusercontent.com/jgutierrezdtt/security-platform/main/config/semgrep/rules.yml \
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
gh api repos/jgutierrezdtt/mi-repo/code-scanning/alerts?state=open \
  --jq '.[] | {number:.number, rule:.rule.id, severity:.rule.security_severity_level, file:.most_recent_instance.location.path}'

# Descartar una alerta como falso positivo
gh api repos/jgutierrezdtt/mi-repo/code-scanning/alerts/42 \
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

**Repositorio**: `jgutierrezdtt/mi-repo` | **Rama**: `feature/login` | **Commit**: `a1b2c3d4`

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

## 6. Troubleshooting — Fallos comunes de configuración

### 6.1 El workflow falla con "Resource not accessible by integration"

**Causa:** El workflow no tiene permisos para escribir en el Security tab (SARIF) o para comentar en el PR.

**Diagnóstico:**
```yaml
# En el workflow que llama al reusable, comprueba que tienes estos permisos:
permissions:
  contents: read
  security-events: write   # Necesario para subir SARIF
  pull-requests: write     # Necesario para comentar en el PR
```

**Si usas `inherit` para pasar secretos, los permisos también deben ser explícitos en el caller.**

---

### 6.2 El secret `EXCEPTIONS_READER_TOKEN` da error 401

**Causa:** El token expiró, se revocó, o no tiene el permiso correcto.

**Diagnóstico en el log de Actions:**
```
→ Obteniendo excepciones globales...
HTTP_CODE: 401
```

**Solución paso a paso:**
1. Ir a GitHub → Settings → Developer settings → Fine-grained personal access tokens
2. Crear un nuevo token con:
   - **Resource owner:** `jgutierrezdtt`
   - **Repository access:** Solo `security-exceptions`
   - **Permissions:** `Contents: Read`
3. Actualizar el secret en el repo consumer:
   ```bash
   gh secret set EXCEPTIONS_READER_TOKEN --repo jgutierrezdtt/mi-repo
   ```
4. El workflow continúa aunque el token falle (usa `continue-on-error`) pero no filtrará excepciones. Confirma en el log que dice `global-exceptions-loaded=true`.

---

### 6.3 El SARIF no aparece en el Security tab

**Causas posibles:**

| Causa | Diagnóstico | Solución |
|-------|-------------|----------|
| GHAS no está habilitado | Security tab muestra "Enable code scanning" | Habilitar en Settings → Security → Code scanning |
| Permiso `security-events: write` falta | Log: "Resource not accessible" | Añadir permiso al workflow caller |
| El repositorio es privado sin GHAS | No hay error visible, simplemente no aparece | Requiere GitHub Advanced Security o hacer el repo público |
| El step de upload usa `if: always()` pero falla silenciosamente | `continue-on-error: true` oculta el error | Quitar temporalmente `continue-on-error` para ver el error real |

**Verificar que el SARIF se subió:**
```bash
gh api repos/jgutierrezdtt/mi-repo/code-scanning/analyses \
  --jq '.[] | {tool:.tool.name, created_at:.created_at, sarif_id:.sarif_id}' \
  | head -5
```

---

### 6.4 El PR comment no aparece

**Causa más común:** El workflow caller no tiene `pull-requests: write`.

**Causa secundaria:** El step usa `marocchino/sticky-pull-request-comment@v2` con `continue-on-error: true`, lo que oculta el fallo. Para depurar:

```bash
# Ver los últimos runs del workflow
gh run list --repo jgutierrezdtt/mi-repo --workflow=security.yml --limit 5

# Ver los logs del run fallido (sustituye <RUN_ID>)
gh run view <RUN_ID> --repo jgutierrezdtt/mi-repo --log | grep -A5 "Post PR comment"
```

---

### 6.5 Semgrep no detecta ningún hallazgo en un repo que sí tiene vulnerabilidades

**Causas y diagnóstico:**

1. **`scan-scope: diff` en un push a main** — Solo analiza el diff. En un push directo a `main` donde no hay PR, el diff puede ser vacío. Usar `scan-scope: full` en el trigger `push`.

2. **El archivo está en `.semgrepignore`** — Verificar con:
   ```bash
   semgrep scan --config config/semgrep/rules.yml --verbose src/archivo-sospechoso.py 2>&1 | grep -i "ignor"
   ```

3. **La regla no aplica al lenguaje del archivo** — Cada regla tiene `languages:`. Un archivo `.ts` no activa una regla que solo aplica a `python`.

4. **El patrón de la regla no hace match** — Probar la regla en el Semgrep Playground: [semgrep.dev/playground](https://semgrep.dev/playground)

---

### 6.6 El security gate bloquea PRs pero el status check no está configurado como required

**Síntoma:** El workflow falla (exit code 1) pero el developer puede mergear igualmente.

**Solución:** Añadir el status check como required en branch protection:
```bash
# Ver los checks disponibles (requiere haber ejecutado el workflow al menos una vez)
gh api repos/jgutierrezdtt/mi-repo/branches/main/protection \
  --jq '.required_status_checks.contexts'

# Añadir el check como required (nombre exacto del job en el workflow)
gh api repos/jgutierrezdtt/mi-repo/branches/main/protection \
  -X PUT \
  --field required_status_checks='{"strict":true,"contexts":["Semgrep SAST / semgrep-scan"]}'
```

El nombre del check sigue el patrón: `<nombre del job caller> / <nombre del job en el reusable>`.

---

## 7. Gestión del ciclo de vida de las reglas Semgrep

### 7.1 Estructura de ficheros de reglas

```
config/semgrep/
├── rules.yml          ← Reglas propias de la organización (revisadas por security-team)
├── .semgrepignore     ← Patrones de exclusión globales
└── rulesets/
    ├── critical.yml   ← Reglas que siempre bloquean (CRITICAL)
    ├── high.yml       ← Reglas de alta severidad
    └── audit.yml      ← Solo informativas (no bloquean)
```

Todos los archivos están en `security-platform`. Cuando se actualizan, todos los repos consumer reciben el cambio automáticamente en su siguiente ejecución — sin PRs en los repos consumer.

### 7.2 Añadir una nueva regla

**Proceso obligatorio (no se añaden reglas directamente a main):**

1. Crear una rama en `security-platform`:
   ```bash
   git checkout -b feat/regla-command-injection
   ```

2. Escribir la regla en `config/semgrep/rules.yml` o en el ruleset correspondiente.

3. **Testear la regla antes de hacer PR:**
   ```bash
   # Probar contra un archivo de test
   semgrep scan \
     --config config/semgrep/rules.yml \
     --include "*.py" \
     tests/fixtures/vulnerable-samples/
   
   # Verificar que la regla detecta exactamente lo que debe
   # y NO detecta lo que no debe (falsos positivos)
   semgrep scan \
     --config config/semgrep/rules.yml \
     --include "*.py" \
     tests/fixtures/safe-samples/
   ```

4. Añadir casos de test inline en la regla (formato estándar de Semgrep):
   ```yaml
   - id: no-eval-user-input
     pattern: eval($USER_INPUT)
     message: "Eval con input de usuario — posible command injection"
     languages: [javascript]
     severity: ERROR
     # Test cases (semgrep --test)
     # ruleid: no-eval-user-input
     # eval(req.body.code)
     #
     # ok: no-eval-user-input
     # eval("2 + 2")
   ```

5. Ejecutar los tests de la regla:
   ```bash
   semgrep --test config/semgrep/
   ```

6. Abrir PR. El CODEOWNERS requiere aprobación de `@jgutierrezdtt/security-team`.

7. Una vez mergeado, la regla entra en producción en el siguiente workflow run de todos los repos consumer.

### 7.3 Retirar una regla

Antes de eliminar una regla, comprueba cuántos repos y cuántas excepciones activas dependen de ella:

```bash
# Buscar en security-exceptions qué excepciones usan esta rule-id
grep -r "rule_id: nombre-de-la-regla" \
  /ruta/a/security-exceptions/exceptions/
```

Si hay excepciones activas para esa regla, la eliminación de la regla las convierte en huérfanas (inofensivas, pero confusas). Documenta la retirada en el PR.

### 7.4 Escalar la severidad de una regla

Cambiar `severity: WARNING` a `severity: ERROR` hará que PRs que antes pasaban ahora fallen. Proceso recomendado:

1. Primero cambia a `ERROR` pero con `fail-on-severity: critical` en los repos consumer → la regla aparece en el reporte pero no bloquea.
2. Comunica a los equipos afectados con **2 semanas de antelación**.
3. Después cambia `fail-on-severity` a `high` en el workflow reusable.

### 7.5 Reglas comunitarias vs reglas propias

| Tipo | Cómo se activa | Mantenimiento | Cuándo usar |
|------|---------------|---------------|-------------|
| Reglas propias (`config/semgrep/rules.yml`) | Automático (en el workflow) | Tú | Patrones específicos del stack o de las políticas internas |
| Rulesets de la comunidad (`p/owasp-top-ten`, etc.) | Via input `semgrep-rules` | Semgrep Inc. | OWASP, CVEs conocidos, buenas prácticas generales |
| Semgrep Pro rules | Via `SEMGREP_APP_TOKEN` | Semgrep Inc. | Detección avanzada, análisis de flujo de datos (taint) |

Las reglas comunitarias se actualizan automáticamente con cada nueva versión de Semgrep. Fija la versión en el workflow si necesitas estabilidad:
```yaml
# En semgrep-scan.yml, la versión está fijada
run: pip install semgrep==1.70.0
```

---

## 8. Coexistencia con un segundo SAST — Evitar duplicados

Si decides añadir un segundo SAST (CodeQL, SonarQube, Snyk Code) junto a Semgrep, el mayor riesgo es **ruido por duplicados**: el mismo hallazgo reportado por dos herramientas, con IDs distintos, sin forma de correlacionarlos.

### 8.1 Qué detecta cada herramienta y dónde se solapan

| Categoría | Semgrep | CodeQL | SonarQube | Snyk Code |
|-----------|---------|--------|-----------|-----------|
| Hardcoded secrets | ✅ (reglas propias) | ⚠️ Limitado | ⚠️ Limitado | ✅ |
| SQL Injection | ✅ | ✅ (taint analysis) | ✅ | ✅ |
| XSS | ✅ | ✅ | ✅ | ✅ |
| Command injection | ✅ | ✅ | ✅ | ✅ |
| Reglas personalizadas | ✅ Muy fácil | ⚠️ Complejo (QL) | ⚠️ Sí, pero caro | ❌ |
| Análisis de flujo (taint) | ⚠️ Solo con Pro | ✅ | ✅ | ✅ |
| Calidad de código | ❌ | ❌ | ✅ | ❌ |
| Dependencias vulnerables | ❌ | ❌ | ✅ | ✅ (SCA) |

**Solapamiento crítico:** SQL Injection, XSS, Command Injection y Hardcoded Secrets son detectados por todas las herramientas.

### 8.2 Estrategia de partición de responsabilidades

En lugar de ejecutar todo en paralelo y gestionar duplicados, asigna responsabilidades distintas:

```
Semgrep          →  Reglas propias de la org + patrones del stack específico
CodeQL           →  Análisis de flujo de datos complejo (taint analysis)
Snyk / Dependabot → Dependencias vulnerables (SCA)
SonarQube        →  Calidad de código + cobertura (fuera del scope de seguridad)
```

Con esta partición, cada herramienta reporta cosas distintas y los duplicados son excepcionales.

### 8.3 Configurar Semgrep para no solaparse con CodeQL

Si usas CodeQL para taint analysis, deshabilita en Semgrep los rulesets que se solapan:

```yaml
# En tu llamada al workflow, no actives los rulesets que CodeQL ya cubre
jobs:
  semgrep:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable/semgrep-scan.yml@main
    with:
      semgrep-rules: >-
        p/default
        # NO incluir p/security-audit — CodeQL lo cubre mejor con taint analysis
        # NO incluir p/nodejs si usas CodeQL para JS
```

Y en `config/semgrep/rules.yml`, añade el tag `duplicate-coverage: codeql` en las reglas que CodeQL ya cubre para tenerlas documentadas pero silenciadas:

```yaml
- id: sql-injection-string-concat
  # ...
  metadata:
    category: security
    duplicate-coverage: codeql   # CodeQL detecta esto con mayor precisión
  severity: WARNING              # Bajar de ERROR a WARNING para no bloquear dos veces
```

### 8.4 Gestión de alertas duplicadas en el Security tab

Cuando dos herramientas suben SARIF, GitHub las muestra por separado en el Security tab. Para evitar confusión:

1. **Usa categorías SARIF distintas** — el workflow de Semgrep usa `category: semgrep`, CodeQL usa `category: javascript` o `category: python`. Las alertas no se mezclan.

2. **Descartar en una sola herramienta** — cuando descartas una alerta como falso positivo, hazlo en la herramienta que "es responsable" según tu partición de responsabilidades. No descartes en ambas.

3. **Correlacionar por localización** — si el mismo archivo y línea aparecen en dos herramientas, es un duplicado real. GitHub no los une automáticamente, pero puedes identificarlos:
   ```bash
   # Ver todas las alertas abiertas con su localización
   gh api repos/jgutierrezdtt/mi-repo/code-scanning/alerts?state=open&per_page=100 \
     --jq '.[] | {tool:.tool.name, rule:.rule.id, file:.most_recent_instance.location.path, line:.most_recent_instance.location.start_line}' \
     | sort
   ```

4. **Si hay más de 2 herramientas**, considera usar una plataforma de correlación (Defect Dojo, OWASP ZAP integration) para unificar resultados antes de que lleguen a GitHub.

### 8.5 Checklist al añadir un segundo SAST

- [ ] Definir qué categorías de vulnerabilidad cubre cada herramienta (sin solapamiento)
- [ ] Ajustar los rulesets de Semgrep para excluir lo que el nuevo SAST cubre mejor
- [ ] Revisar el `fail-on-severity` de cada herramienta — dos herramientas bloqueando el mismo PR por el mismo hallazgo genera confusión
- [ ] Comunicar a los equipos que verán más alertas inicialmente (efecto de calibración)
- [ ] Establecer un proceso claro: ¿en qué herramienta se gestiona cada tipo de hallazgo?
- [ ] Revisar que las excepciones en `security-exceptions` especifican `tool:` para que solo apliquen a Semgrep y no silencien hallazgos de CodeQL

---

## 9. Checklist

- [ ] Secret `SEMGREP_APP_TOKEN` configurado (si se usa Semgrep Cloud)
- [ ] Secret `EXCEPTIONS_READER_TOKEN` configurado
- [ ] Workflow de seguridad creado en el repositorio consumer
- [ ] `.semgrepignore` creado para excluir tests y código generado
- [ ] Code Scanning habilitado en el repositorio (para ver SARIF)
- [ ] Status check `Semgrep SAST` añadido como required en branch protection
- [ ] Revisión de los primeros resultados y validación de reglas
- [ ] Si se añade un segundo SAST: responsabilidades de cobertura particionadas

---

## Siguiente paso

➡️ [Tutorial 08 — Gestión de Excepciones](08-exception-management.md)
