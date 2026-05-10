# Tutorial 02 — Protección de Ramas

> **Audiencia**: Administradores de repositorios  
> **Nivel**: Intermedio-Avanzado  
> **Tiempo estimado**: 60 minutos  
> **Prerrequisitos**: Tutorial 01 completado, acceso de administrador

---

## ¿Qué cubre este tutorial?

GitHub ofrece dos mecanismos para proteger ramas:

1. **Branch Protection Rules** (clásico, por repositorio)
2. **Repository Rulesets** (moderno, heredable desde la organización) ← **Recomendado**

Este tutorial cubre **ambos**, con énfasis en Rulesets por ser el estándar actual para organizaciones grandes.

---

## 1. Branch Protection Rules (clásico)

### 1.1 Proteger la rama `main` vía CLI

```bash
gh api repos/jgutierrezdtt/mi-repo/branches/main/protection \
  -X PUT \
  --field required_status_checks='{"strict":true,"contexts":["Semgrep SAST","Dependabot Status"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":2,"dismiss_stale_reviews":true,"require_code_owner_reviews":true}' \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field required_linear_history=true \
  --field required_conversation_resolution=true \
  --field lock_branch=false
```

### 1.2 Descripción de cada parámetro

| Parámetro | Valor | Razón |
|-----------|-------|-------|
| `required_status_checks.strict` | `true` | El PR debe estar actualizado con la rama base antes de mergear |
| `required_status_checks.contexts` | `["Semgrep SAST","Dependabot Status"]` | Los checks de seguridad son **obligatorios** para mergear |
| `enforce_admins` | `true` | Los admins también deben cumplir las reglas |
| `required_approving_review_count` | `2` | Mínimo 2 aprobaciones |
| `dismiss_stale_reviews` | `true` | Nuevos commits invalidan las aprobaciones anteriores |
| `require_code_owner_reviews` | `true` | Los CODEOWNERS deben aprobar cambios en su área |
| `allow_force_pushes` | `false` | Prohibir force push para preservar el historial |
| `allow_deletions` | `false` | Prohibir eliminar la rama protegida |
| `required_linear_history` | `true` | Solo se permite merge lineal (squash o rebase) |
| `required_conversation_resolution` | `true` | Todos los comentarios deben estar resueltos |

---

## 2. Repository Rulesets (moderno — RECOMENDADO)

Los Rulesets son la evolución de Branch Protection. Sus ventajas clave:

- ✅ **Heredables**: se pueden definir a nivel de organización y aplicar a todos los repos
- ✅ **Apilables**: múltiples rulesets pueden coexistir
- ✅ **Bypass list**: se puede definir quién puede saltarse las reglas (de forma auditada)
- ✅ **Granular**: se aplican por patrón de rama, no solo a ramas específicas
- ✅ **API-first**: fácil de gestionar con IaC

### 2.1 Crear un Ruleset para ramas de producción

```bash
gh api repos/jgutierrezdtt/mi-repo/rulesets \
  -X POST \
  --input - << 'EOF'
{
  "name": "production-branch-protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main", "refs/heads/release/**"],
      "exclude": []
    }
  },
  "bypass_actors": [
    {
      "actor_id": 1,
      "actor_type": "OrganizationAdmin",
      "bypass_mode": "always"
    }
  ],
  "rules": [
    {
      "type": "deletion"
    },
    {
      "type": "non_fast_forward"
    },
    {
      "type": "creation"
    },
    {
      "type": "required_linear_history"
    },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 2,
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
          {
            "context": "Semgrep SAST",
            "integration_id": null
          },
          {
            "context": "Dependabot Status",
            "integration_id": null
          }
        ]
      }
    },
    {
      "type": "commit_message_pattern",
      "parameters": {
        "name": "Conventional Commits",
        "negate": false,
        "operator": "regex",
        "pattern": "^(feat|fix|docs|style|refactor|perf|test|chore|ci|security)(\\(.+\\))?: .{1,72}"
      }
    },
    {
      "type": "committer_email_pattern",
      "parameters": {
        "name": "Corporate email",
        "negate": false,
        "operator": "ends_with",
        "pattern": "@jgutierrezdtt.com"
      }
    },
    {
      "type": "tag_name_pattern",
      "parameters": {
        "name": "Semantic versioning",
        "negate": false,
        "operator": "regex",
        "pattern": "^v[0-9]+\\.[0-9]+\\.[0-9]+(-[a-zA-Z0-9.]+)?$"
      }
    }
  ]
}
EOF
```

### 2.2 Ruleset a nivel de organización

Para aplicar protecciones a TODOS los repositorios de la organización:

```bash
gh api orgs/jgutierrezdtt/rulesets \
  -X POST \
  --input - << 'EOF'
{
  "name": "org-wide-main-protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "repository_name": {
      "include": ["~ALL"],
      "exclude": ["security-exceptions"],
      "protected": true
    },
    "ref_name": {
      "include": ["refs/heads/main", "refs/heads/master"],
      "exclude": []
    }
  },
  "bypass_actors": [
    {
      "actor_id": 1,
      "actor_type": "OrganizationAdmin",
      "bypass_mode": "pull_request"
    }
  ],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
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
        "strict_required_status_checks_policy": false,
        "required_status_checks": []
      }
    }
  ]
}
EOF
```

---

## 3. Configuración para ramas de desarrollo

Las ramas de feature (`feature/**`) tienen reglas menos estrictas pero igualmente importantes:

```bash
gh api repos/jgutierrezdtt/mi-repo/rulesets \
  -X POST \
  --input - << 'EOF'
{
  "name": "feature-branch-rules",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/feature/**", "refs/heads/fix/**", "refs/heads/hotfix/**"],
      "exclude": []
    }
  },
  "rules": [
    { "type": "non_fast_forward" },
    {
      "type": "commit_message_pattern",
      "parameters": {
        "name": "Conventional Commits",
        "negate": false,
        "operator": "regex",
        "pattern": "^(feat|fix|docs|style|refactor|perf|test|chore|ci|security)(\\(.+\\))?: .{1,72}"
      }
    }
  ]
}
EOF
```

---

## 4. Gestión de Rulesets como código (IaC)

Para organizaciones grandes, gestiona los rulesets con Terraform o scripts versionados:

```hcl
# terraform/rulesets/production.tf
resource "github_repository_ruleset" "production_protection" {
  name        = "production-branch-protection"
  repository  = "mi-repo"
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["refs/heads/main", "refs/heads/release/**"]
      exclude = []
    }
  }

  bypass_actors {
    actor_id    = data.github_team.security_team.id
    actor_type  = "Team"
    bypass_mode = "pull_request"
  }

  rules {
    deletion         {}
    non_fast_forward {}
    required_linear_history {}

    pull_request {
      required_approving_review_count   = 2
      dismiss_stale_reviews_on_push     = true
      require_code_owner_review         = true
      require_last_push_approval        = true
      required_review_thread_resolution = true
    }

    required_status_checks {
      strict_required_status_checks_policy = true
      required_check {
        context = "Semgrep SAST"
      }
      required_check {
        context = "Dependabot Status"
      }
    }
  }
}
```

---

## 5. Verificar configuración actual

```bash
#!/usr/bin/env bash
REPO="${1:-jgutierrezdtt/mi-repo}"
BRANCH="${2:-main}"

echo "=== Branch Protection: ${REPO}/${BRANCH} ==="

# Verificar branch protection clásica
gh api "repos/${REPO}/branches/${BRANCH}/protection" 2>/dev/null | \
  jq '{
    enforce_admins: .enforce_admins.enabled,
    required_reviews: .required_pull_request_reviews.required_approving_review_count,
    require_code_owners: .required_pull_request_reviews.require_code_owner_reviews,
    dismiss_stale: .required_pull_request_reviews.dismiss_stale_reviews,
    linear_history: .required_linear_history.enabled,
    allow_force_push: .allow_force_pushes.enabled,
    allow_deletion: .allow_deletions.enabled
  }' || echo "Sin branch protection clásica configurada"

echo ""
echo "=== Rulesets activos ==="
gh api "repos/${REPO}/rulesets" --jq '.[] | {id:.id, name:.name, enforcement:.enforcement}'
```

---

## 6. Checklist

- [ ] Branch `main` protegida con Ruleset o Branch Protection
- [ ] Mínimo **2 aprobaciones** requeridas para PR
- [ ] **CODEOWNERS review** requerido
- [ ] **Dismiss stale reviews** habilitado
- [ ] **Force push** prohibido
- [ ] **Deletion** prohibida
- [ ] **Status checks** de Semgrep y Dependabot como required
- [ ] **Conversaciones resueltas** requeridas antes de merge
- [ ] Ruleset **organizacional** definido para protección base de todos los repos

---

## Siguiente paso

➡️ [Tutorial 03 — Roles y Permisos](03-roles-and-permissions.md)
