# Tutorial 04 — Aprobación de Pull Requests

> **Audiencia**: Tech leads, desarrolladores senior, responsables de equipos  
> **Nivel**: Intermedio  
> **Tiempo estimado**: 40 minutos  
> **Prerrequisitos**: Tutoriales 02 y 03 completados

---

## 1. CODEOWNERS — Propietarios de código

CODEOWNERS define qué equipos o personas deben aprobar cambios en partes específicas del código. Es la base del proceso de revisión obligatoria.

### 1.1 Formato del archivo

```
# .github/CODEOWNERS
# Sintaxis: <patrón>  <propietario1> <propietario2>

# Por defecto, el security-team aprueba todo
*                          @jgutierrezdtt/security-team

# Workflows de seguridad — doble aprobación
.github/workflows/         @jgutierrezdtt/security-team @jgutierrezdtt/platform-team

# Configuración de Semgrep — solo security-team
config/semgrep/            @jgutierrezdtt/security-team

# Documentación — el platform-team puede aprobar
docs/                      @jgutierrezdtt/platform-team @jgutierrezdtt/security-team

# Templates — platform-team con revisión de security
templates/                 @jgutierrezdtt/platform-team @jgutierrezdtt/security-team

# Scripts de infraestructura
scripts/                   @jgutierrezdtt/platform-team
```

### 1.2 Reglas de CODEOWNERS

- El archivo debe estar en `.github/CODEOWNERS`, `CODEOWNERS` o `docs/CODEOWNERS`
- La **última regla** que coincide gana (como `.gitignore`)
- Los propietarios deben ser miembros de la organización o teams existentes
- Para que sea efectivo, debe estar habilitado `require_code_owner_reviews` en la branch protection

### 1.3 Verificar qué CODEOWNERS aplican a un archivo

```bash
# Ver quién es dueño de un archivo específico
gh api repos/jgutierrezdtt/security-platform/codeowners/errors \
  --jq '.errors[]'
```

---

## 2. Required Reviews — Configuración avanzada

### 2.1 Estructura de revisión por capas

Para `security-platform`, usamos un proceso de **doble aprobación**:

```
PR abierto
    │
    ▼
┌─────────────────────────────────┐
│ 1. Checks automáticos (CI/CD)   │ ← Semgrep + Dependabot deben pasar
└─────────────────────────────────┘
    │ ✅ Passed
    ▼
┌─────────────────────────────────┐
│ 2. Code review técnico          │ ← Mínimo 1 reviewer del equipo
└─────────────────────────────────┘
    │ ✅ Approved
    ▼
┌─────────────────────────────────┐
│ 3. CODEOWNERS review            │ ← Dueño del área afectada
└─────────────────────────────────┘
    │ ✅ Approved
    ▼
┌─────────────────────────────────┐
│ 4. Merge (squash recomendado)   │
└─────────────────────────────────┘
```

### 2.2 Templates de Pull Request

Crea un template para estandarizar la descripción de PRs:

```markdown
<!-- .github/PULL_REQUEST_TEMPLATE.md -->
## ¿Qué hace este PR?

<!-- Descripción concisa del cambio -->

## Motivación y contexto

<!-- ¿Por qué es necesario este cambio? -->

## Tipo de cambio

- [ ] 🐛 Bug fix (cambio no disruptivo que soluciona un issue)
- [ ] ✨ Nueva característica (cambio no disruptivo que añade funcionalidad)
- [ ] 💥 Breaking change (fix o feature que cambia comportamiento existente)
- [ ] 🔐 Security fix (corrige una vulnerabilidad)
- [ ] 📝 Documentación

## Checklist

- [ ] El código sigue el estilo del proyecto
- [ ] Revisé mi propio código antes de pedir review
- [ ] Los tests existentes pasan con mis cambios
- [ ] El pipeline de Semgrep pasa sin nuevas alertas críticas/altas
- [ ] El pipeline de Dependabot pasa
- [ ] Documentación actualizada si aplica

## Impacto en seguridad

<!-- Si el cambio tiene implicaciones de seguridad, descríbelas aquí -->
<!-- ¿Se han introducido nuevas dependencias? ¿Cambios en permisos? -->

## Tests relacionados

<!-- Referencias a tests que validan el cambio -->

## Issues relacionados

Closes #<!-- número de issue -->
```

### 2.3 Múltiples templates de PR

Para repos con varios tipos de PR, puedes tener templates específicos:

```
.github/
└── PULL_REQUEST_TEMPLATE/
    ├── bug_fix.md
    ├── feature.md
    ├── security.md          ← Para cambios de seguridad
    └── exception_request.md ← Para solicitar excepciones en Semgrep
```

Los usuarios seleccionan el template añadiendo `?template=security.md` a la URL del PR.

---

## 3. Draft Pull Requests

Los Draft PRs permiten trabajo en progreso sin solicitar review. **Política recomendada**:

- Los checks de CI **deben pasar** incluso en Draft PRs
- Los Semgrep y Dependabot checks corren en Draft para feedback temprano
- El security gate **solo bloquea** en PRs `Ready for Review`

```yaml
# En el workflow reutilizable, detectar si es Draft
- name: Check if PR is draft
  if: github.event.pull_request.draft == true
  run: echo "PR es Draft — ejecutando en modo report-only"

# Adaptar el modo según el estado del PR
- name: Semgrep Scan
  uses: ./.github/workflows/reusable-semgrep-scan.yml
  with:
    report-only: ${{ github.event.pull_request.draft == true }}
```

---

## 4. Auto-merge y merge queues

### 4.1 Habilitar Merge Queue (Enterprise)

La Merge Queue valida que múltiples PRs funcionan juntos antes de mergear:

```bash
gh api repos/jgutierrezdtt/mi-repo \
  -X PATCH \
  --field merge_queue='{
    "enabled": true,
    "merge_strategy": "squash",
    "min_entries_to_merge": 1,
    "max_entries_to_merge": 5,
    "min_entries_to_merge_wait_minutes": 5,
    "check_response_timeout_minutes": 60
  }'
```

### 4.2 Auto-merge para Dependabot

```yaml
# .github/workflows/dependabot-auto-merge.yml
name: Auto-merge Dependabot PRs (patch/minor)

on:
  pull_request:

permissions:
  contents: write
  pull-requests: write

jobs:
  auto-merge:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - name: Fetch Dependabot metadata
        id: metadata
        uses: dependabot/fetch-metadata@v2
        with:
          github-token: "${{ secrets.GITHUB_TOKEN }}"

      - name: Auto-merge patch and minor updates
        if: |
          steps.metadata.outputs.update-type == 'version-update:semver-patch' ||
          steps.metadata.outputs.update-type == 'version-update:semver-minor'
        run: |
          gh pr merge --auto --squash "${{ github.event.pull_request.html_url }}"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

> **Seguridad**: El auto-merge de Dependabot solo aplica para actualizaciones patch/minor. Las actualizaciones major siempre requieren revisión manual.

---

## 5. Revisión de seguridad especial

Para cambios de alta sensibilidad (modificaciones a workflows, config de Semgrep, excepciones), aplica el proceso de **Dual Control**:

```yaml
# CODEOWNERS — Dual control para archivos críticos
# Requiere aprobación de DOS personas distintas del security-team
.github/workflows/ (reusable-)    @jgutierrezdtt/security-team
config/semgrep/               @jgutierrezdtt/security-team
```

Con `required_approving_review_count: 2` en branch protection, si el security-team tiene ≥2 miembros, ambos deben aprobar.

---

## 6. Checklist

- [ ] `.github/CODEOWNERS` definido y probado
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` creado
- [ ] Branch protection requiere **CODEOWNERS review**
- [ ] Branch protection requiere mínimo **2 aprobaciones** para `main`
- [ ] **Dismiss stale reviews** habilitado
- [ ] **Conversations resolved** requerido antes de merge
- [ ] Draft PRs configurados para **report-only** en security checks
- [ ] **Auto-merge** de Dependabot habilitado solo para patch/minor
- [ ] Proceso documentado de revisión de seguridad para cambios críticos

---

## Siguiente paso

➡️ [Tutorial 05 — SLSA en Pipelines](05-slsa-pipelines.md)
