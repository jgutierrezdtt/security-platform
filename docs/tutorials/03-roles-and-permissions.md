# Tutorial 03 — Roles y Permisos

> **Audiencia**: Administradores de organización, Engineering Managers  
> **Nivel**: Intermedio  
> **Tiempo estimado**: 45 minutos  
> **Prerrequisitos**: Acceso de Owner en la organización

---

## Modelo de permisos en GitHub

GitHub usa un sistema de permisos en capas:

```
Organización
  └── Teams
        └── Repositorios
              └── Roles base (Read, Triage, Write, Maintain, Admin)
                    └── Roles personalizados (GitHub Enterprise)
```

---

## 1. Roles base de repositorio

| Rol | Descripción | Uso típico |
|-----|-------------|------------|
| **Read** | Ver código, crear issues, comentar | Stakeholders, auditores externos |
| **Triage** | Gestionar issues y PRs sin escribir código | Project managers, QA |
| **Write** | Push a ramas no protegidas, crear PRs | Desarrolladores |
| **Maintain** | Gestionar el repo (settings, webhooks) | Tech leads |
| **Admin** | Control total, incluyendo protección de ramas | Pocos, solo responsables directos |

---

## 2. Estructura de Teams recomendada para jgutierrezdtt

```
jgutierrezdtt (org)
├── @jgutierrezdtt/security-team        → Admin en security-platform y exceptions
├── @jgutierrezdtt/platform-team        → Maintain en security-platform
├── @jgutierrezdtt/developers           → Write en repos de desarrollo
├── @jgutierrezdtt/leads               → Maintain en sus repos
└── @jgutierrezdtt/external-reviewers  → Read en repos seleccionados
```

### 2.1 Crear los teams

```bash
# Team de seguridad (private — solo visible para miembros)
gh api orgs/jgutierrezdtt/teams \
  -X POST \
  --field name="security-team" \
  --field description="Equipo de seguridad - gestiona políticas y excepciones" \
  --field privacy="secret"

# Team de plataforma
gh api orgs/jgutierrezdtt/teams \
  -X POST \
  --field name="platform-team" \
  --field description="Ingeniería de plataforma - mantiene las pipelines centrales" \
  --field privacy="closed"

# Team de desarrolladores (base)
gh api orgs/jgutierrezdtt/teams \
  -X POST \
  --field name="developers" \
  --field description="Todos los desarrolladores de la organización" \
  --field privacy="closed"
```

### 2.2 Asignar permisos de team a repositorios

```bash
# security-team → Admin en security-platform
gh api orgs/jgutierrezdtt/teams/security-team/repos/jgutierrezdtt/security-platform \
  -X PUT --field permission=admin

# security-team → Admin en security-exceptions (con control exclusivo)
gh api orgs/jgutierrezdtt/teams/security-team/repos/jgutierrezdtt/security-exceptions \
  -X PUT --field permission=admin

# platform-team → Maintain en security-platform
gh api orgs/jgutierrezdtt/teams/platform-team/repos/jgutierrezdtt/security-platform \
  -X PUT --field permission=maintain

# developers → Read en security-exceptions (solo consulta)
gh api orgs/jgutierrezdtt/teams/developers/repos/jgutierrezdtt/security-exceptions \
  -X PUT --field permission=pull

# developers → Read en security-platform (para consultar docs y templates)
gh api orgs/jgutierrezdtt/teams/developers/repos/jgutierrezdtt/security-platform \
  -X PUT --field permission=pull
```

---

## 3. Roles personalizados (GitHub Enterprise)

Para organizaciones con GitHub Enterprise, puedes crear roles con permisos granulares:

```bash
# Crear rol "Security Reviewer" — puede ver alertas pero no modificar código
gh api orgs/jgutierrezdtt/custom_roles \
  -X POST \
  --input - << 'EOF'
{
  "name": "Security Reviewer",
  "description": "Puede revisar alertas de seguridad y aprobar excepciones",
  "base_role": "read",
  "permissions": [
    "read_code_scanning",
    "read_secret_scanning",
    "read_dependabot_alerts",
    "write_discussions",
    "pull_requests_merge"
  ]
}
EOF
```

---

## 4. Permisos de GitHub Apps y tokens

### 4.1 Fine-grained Personal Access Tokens (PATs)

Para el sistema de excepciones, se usa un PAT con permisos mínimos:

```
Token: EXCEPTIONS_READER_TOKEN
Permisos:
  - Repository: Contents → Read-only
  - Repository: Metadata → Read-only (implícito)
```

```bash
# Verificar los permisos de un token (sin exponer el token)
gh api user --auth-token "$EXCEPTIONS_READER_TOKEN" | jq '.login'

# Ver los repos a los que tiene acceso
gh api user/repos --auth-token "$EXCEPTIONS_READER_TOKEN" \
  --jq '.[].full_name'
```

### 4.2 GitHub Apps (recomendado para producción)

Para organizaciones grandes, usa una GitHub App en lugar de PATs:

```bash
# Registrar la app via API
gh api orgs/jgutierrezdtt/installations \
  --jq '.[].app_slug'
```

**Ventajas de GitHub Apps vs PATs**:
| Característica | Fine-grained PAT | GitHub App |
|----------------|-----------------|------------|
| Vinculado a usuario | ✅ Sí (riesgo si sale el empleado) | ❌ No (org-level) |
| Granularidad de permisos | Alta | Muy alta |
| Rate limit | 5,000 req/h | 15,000 req/h |
| Auditoría | Por usuario | Por instalación |
| Rotación | Manual | Automática (tokens 1h) |
| **Recomendado para CI/CD** | No ideal | ✅ Sí |

---

## 5. Principio de menor privilegio en workflows

Los workflows de GitHub Actions deben declarar permisos explícitamente:

```yaml
# En el workflow llamante (consumer)
jobs:
  semgrep:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-semgrep-scan.yml@main
    # Nunca dar permisos extras. Los reusable workflows solo pueden usar lo que declaran.
    secrets:
      EXCEPTIONS_READER_TOKEN: ${{ secrets.EXCEPTIONS_READER_TOKEN }}
```

```yaml
# En el workflow reutilizable (security-platform)
jobs:
  semgrep:
    runs-on: ubuntu-latest
    permissions:
      contents: read           # ← Solo lo mínimo necesario
      security-events: write   # ← Para subir SARIF
      pull-requests: write     # ← Para comentar en PRs
```

> **Regla**: Nunca uses `permissions: write-all` en un workflow. Siempre declara permisos específicos.

---

## 6. Gestión de miembros de la organización

### 6.1 Configurar el rol base de la organización

```bash
# Configurar que los nuevos miembros tengan rol "member" (no owner)
gh api orgs/jgutierrezdtt \
  -X PATCH \
  --field default_repository_permission=none \
  --field members_can_create_repositories=false \
  --field members_can_create_private_repositories=false
```

> En jgutierrezdtt, **ningún desarrollador tiene permisos por defecto**. Solo los que pertenecen a los teams configurados.

### 6.2 Requerir 2FA en toda la organización

```bash
gh api orgs/jgutierrezdtt \
  -X PATCH \
  --field two_factor_requirement_enabled=true
```

### 6.3 Auditar miembros y permisos

```bash
#!/usr/bin/env bash
echo "=== Miembros con rol Owner ==="
gh api orgs/jgutierrezdtt/members?role=owner \
  --jq '.[].login'

echo ""
echo "=== Colaboradores externos ==="
gh api orgs/jgutierrezdtt/outside_collaborators \
  --jq '.[].login'

echo ""
echo "=== Teams y sus miembros ==="
gh api orgs/jgutierrezdtt/teams \
  --jq '.[] | .name' | while read team; do
    echo "--- ${team} ---"
    gh api "orgs/jgutierrezdtt/teams/${team}/members" --jq '.[].login'
  done
```

---

## 7. Política de acceso de terceros

Para colaboradores externos (contratistas, auditores):

```bash
# Añadir colaborador con permisos de Read
gh api repos/jgutierrezdtt/mi-repo/collaborators/username-externo \
  -X PUT \
  --field permission=pull

# Establecer fecha de expiración (pendiente de función nativa en GitHub)
# Usar GitHub Apps con expiry o gestionar manualmente con recordatorios
```

**Proceso para externos**:
1. Solicitud aprobada por el responsable del equipo
2. Acceso mínimo necesario (Pull por defecto)
3. Revisión trimestral de accesos externos
4. Eliminación inmediata al terminar el contrato

---

## 8. Checklist

- [ ] **Owners** de la org limitados al mínimo (máximo 3 personas)
- [ ] **2FA obligatorio** en toda la organización
- [ ] **Teams** creados y con permisos asignados a repos
- [ ] **EXCEPTIONS_READER_TOKEN** es un Fine-grained PAT con permisos mínimos
- [ ] **Desarrolladores** no tienen permisos por defecto
- [ ] **Colaboradores externos** auditados trimestralmente
- [ ] **Workflows** con permisos explícitos (no `write-all`)
- [ ] **GitHub App** creada para integraciones de CI/CD (en lugar de PATs personales)

---

## Siguiente paso

➡️ [Tutorial 04 — Aprobación de Pull Requests](04-pull-request-approvals.md)
