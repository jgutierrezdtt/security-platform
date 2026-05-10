# Tutorial 08 — Gestión de Excepciones y Falsos Positivos

> **Audiencia**: Desarrolladores, security team  
> **Nivel**: Intermedio  
> **Tiempo estimado**: 45 minutos

---

## Introducción

No todos los hallazgos de Semgrep representan vulnerabilidades reales. Un **falso positivo** es un hallazgo que la herramienta reporta como problema, pero que en el contexto real del código no representa un riesgo de seguridad.

El sistema de gestión de excepciones de `jgutierrezdtt` está diseñado con estos principios:

| Principio | Implementación |
|-----------|---------------|
| **Centralizado** | Un único repositorio de excepciones para toda la organización |
| **Auditado** | Toda excepción requiere aprobación del security-team |
| **Trazable** | Cada excepción tiene justificación, fecha y firmante |
| **Temporal** | Las excepciones tienen fecha de expiración |
| **Read-only** | Los repos solo pueden leer excepciones, no modificarlas |
| **Revisable** | Revisión periódica para validar que siguen siendo válidas |

---

## 1. Arquitectura del sistema de excepciones

```
jgutierrezdtt/security-exceptions (repo)
│
│ ← Solo security-team puede escribir
│ ← Todos los repos pueden leer (con EXCEPTIONS_READER_TOKEN)
│
├── exceptions/
│   ├── global/
│   │   └── false-positives.yml       ← Excepciones para toda la org
│   └── by-repo/
│       ├── frontend-app__frontend-app/
│       │   └── exceptions.yml        ← Excepciones del repo frontend-app
│       └── api-service__api-service/
│           └── exceptions.yml
│
└── schemas/
    └── exception.schema.json         ← Validación automática de formato
```

Durante el scan, el workflow reutilizable:
1. Descarga las excepciones globales
2. Descarga las excepciones específicas del repo (si existen)
3. Filtra los hallazgos que coincidan con alguna excepción
4. Reporta los hallazgos filtrados como "exceptuados" (para auditoría)

---

## 2. Solicitar una excepción — Proceso paso a paso

### Paso 1: Identificar el hallazgo

Cuando Semgrep bloquea tu PR, el comentario incluye detalles del hallazgo:

```
| 1 | 🟠 HIGH | `sql-injection-string-concat` | `src/db/queries.js` | 45 | SQL injection... |
```

Copia la **regla ID** (`sql-injection-string-concat`) y el **path** (`src/db/queries.js`).

### Paso 2: Analizar si es realmente un falso positivo

Antes de solicitar una excepción, responde estas preguntas:

- ¿El input en ese punto **ya está sanitizado** por código upstream?
- ¿Es código de test que **nunca llega a producción**?
- ¿Es código **generado automáticamente** que no puedo modificar?
- ¿La vulnerabilidad **no es explotable** en el contexto de la aplicación?

Si la respuesta es "no" a todas, **primero corrige el código**.

### Paso 3: Abrir un Issue en security-exceptions

Ve a [jgutierrezdtt/security-exceptions/issues/new?template=exception-request.yml](https://github.com/jgutierrezdtt/security-exceptions/issues/new?template=exception-request.yml) y completa el formulario:

```yaml
# Información requerida en el issue:
Repositorio afectado: jgutierrezdtt/frontend-app
Regla de Semgrep: sql-injection-string-concat
Archivo y línea: src/db/queries.js:45
Severidad: HIGH
Justificación: El parámetro userId es validado y casteado a integer en el middleware
                de autenticación (src/middleware/auth.js:23) antes de llegar a esta función.
                Verificado con el security-team que no es explotable.
Tipo de excepción: false_positive
Fecha de expiración propuesta: 2027-05-10
```

### Paso 4: Revisión por el security-team

El security-team revisará:
1. ¿La justificación es técnicamente correcta?
2. ¿Se puede verificar en el código?
3. ¿La excepción es lo suficientemente específica? (no demasiado amplia)
4. ¿Tiene fecha de expiración razonable?

Si se aprueba, el security-team añade la excepción al repositorio.

---

## 3. Formato de excepciones

### 3.1 Excepciones globales (falsos positivos de reglas)

```yaml
# exceptions/global/false-positives.yml
schema_version: "1.0"
last_updated: "2026-05-10"
updated_by: "@jgutierrezdtt/security-team"

exceptions:
  # ─── Falso positivo conocido en pytest fixtures ──────────────
  - id: "EXC-GLOBAL-001"
    rule_id: "no-hardcoded-api-keys"
    path: "tests/fixtures/**"           # Glob pattern — aplica a todos los repos
    severity: HIGH
    type: false_positive
    justification: |
      Los archivos de fixtures de pytest contienen claves API falsas
      documentadas explícitamente para pruebas. Nunca se usan en producción.
      Todas las claves de fixture siguen el patrón: test-*-key-do-not-use.
    approved_by: "@security-lead"
    approved_at: "2026-01-15"
    expires_at: "2027-01-15"
    review_notes: "Revisado y confirmado. Las keys de test tienen prefijo 'test-'."

  # ─── Regla con alta tasa de FP en configs de desarrollo ──────
  - id: "EXC-GLOBAL-002"
    rule_id: "debug-mode-production"
    path: "**/.env.development"
    severity: WARNING
    type: false_positive
    justification: |
      Los archivos .env.development son explícitamente para entorno local.
      Están en .gitignore y nunca se despliegan a producción.
    approved_by: "@security-lead"
    approved_at: "2026-02-01"
    expires_at: "2027-02-01"
```

### 3.2 Excepciones por repositorio

```yaml
# exceptions/by-repo/frontend-app__frontend-app/exceptions.yml
schema_version: "1.0"
repository: "jgutierrezdtt/frontend-app"
last_updated: "2026-05-10"

exceptions:
  - id: "EXC-FRONTEND-001"
    rule_id: "sql-injection-string-concat"
    path: "src/db/queries.js"
    line: 45                            # Línea específica para mayor precisión
    severity: HIGH
    type: false_positive
    justification: |
      El parámetro userId es validado y casteado a integer en el middleware
      de autenticación (src/middleware/auth.js:23). No es posible inyección SQL
      porque el valor siempre será un entero válido en este punto de ejecución.
    approved_by: "@security-analyst"
    approved_at: "2026-05-10"
    expires_at: "2026-11-10"           # 6 meses — revisión semestral
    ticket: "SEC-2026-042"             # Ticket en el sistema de tracking interno
    pr_reference: "jgutierrezdtt/security-exceptions#15"

  - id: "EXC-FRONTEND-002"
    rule_id: "no-log-sensitive-data"
    path: "src/services/auth.service.js"
    line: 78
    severity: WARNING
    type: accepted_risk
    justification: |
      Se loggea el hash del token (no el token en claro) para debugging de autenticación.
      El hash SHA-256 no permite recuperar el token original.
      Riesgo residual aceptado por el CISO el 2026-05-01.
    approved_by: "@ciso"
    approved_at: "2026-05-01"
    expires_at: "2026-12-01"
    review_notes: "Revisar cuando se implemente el nuevo sistema de logging estructurado."
```

---

## 4. Usar `# nosemgrep` como excepción inline (con criterio)

Para casos muy específicos, Semgrep permite suprimir un hallazgo con un comentario inline:

```python
# ✅ USO CORRECTO — con justificación y referencia
user_id = int(request.args.get('user_id'))  # nosemgrep: sql-injection-string-concat — input casteado a int
db.query(f"SELECT * FROM users WHERE id = {user_id}")
```

```javascript
// ❌ MAL — sin justificación, oscurece el hallazgo
eval(userInput)  // nosemgrep
```

**Política de `nosemgrep` en jgutierrezdtt:**
1. Solo se permite con un comentario que explique **por qué**
2. Debe incluir la **regla suprimida** explícitamente
3. Los `nosemgrep` sin comentario son bloqueados por la regla `no-bare-nosemgrep`
4. Preferir excepciones en el repositorio central sobre `nosemgrep` inline

---

## 5. Caducidad y revisión de excepciones

El workflow de validación en `security-exceptions` alerta cuando:
- Una excepción está a menos de **30 días de expirar**
- Una excepción ya ha **expirado**

```bash
# Script de revisión manual
python3 << 'EOF'
import yaml
from datetime import datetime, timedelta
from pathlib import Path

today = datetime.now()
warning_threshold = today + timedelta(days=30)

for yml_file in Path("exceptions").rglob("*.yml"):
    with open(yml_file) as f:
        data = yaml.safe_load(f) or {}
    
    for exc in data.get("exceptions", []):
        expiry = exc.get("expires_at")
        if expiry:
            expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
            if expiry_date < today:
                print(f"❌ EXPIRADA: {exc['id']} en {yml_file}")
            elif expiry_date < warning_threshold:
                days_left = (expiry_date - today).days
                print(f"⚠️  PRÓXIMA EXPIRACIÓN ({days_left} días): {exc['id']} en {yml_file}")
EOF
```

---

## 6. Checklist

- [ ] El proceso de solicitud de excepción está documentado para el equipo
- [ ] Solo el `@jgutierrezdtt/security-team` puede aprobar y añadir excepciones
- [ ] Cada excepción tiene **justificación técnica**, **aprobador** y **fecha de expiración**
- [ ] El workflow de validación verifica el formato de las excepciones
- [ ] Las excepciones caducadas se revisan en plazo (≤30 días)
- [ ] `nosemgrep` inline requiere comentario justificativo (validado en pipeline)
- [ ] `EXCEPTIONS_READER_TOKEN` es un PAT read-only, nunca write

---

## Siguiente paso

➡️ [Tutorial 09 — Security Gates](09-security-gates.md)
