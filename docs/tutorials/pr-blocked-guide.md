# Mi PR esta bloqueado por seguridad — que hago

> Esta guia es para el developer que ve un check de seguridad en rojo en su PR.
> No asume conocimiento previo del sistema. Explica que paso dar segun lo que ves.

---

## Primero: leer el comentario del PR

El sistema deja un comentario en tu PR con el detalle de lo que ha encontrado.
Tiene este aspecto (simplificado):

```
Semgrep Security Scan — Resultados

Estado: BLOQUEADO — Vulnerabilidades Altas

Hallazgos Activos

# | Severidad | Regla                       | Archivo              | Linea
1 | HIGH      | sql-injection-string-concat  | src/db/queries.py    | 45
2 | HIGH      | no-hardcoded-api-keys        | config/settings.py   | 12
3 | MEDIUM    | debug-mode-production        | .env                 | 3
```

El check solo bloquea el merge si hay hallazgos HIGH o CRITICAL sin excepcion aprobada.
Los MEDIUM y LOW aparecen en el reporte pero no bloquean.

---

## Segundo: identificar de que tipo es el hallazgo

Hay tres situaciones posibles:

### Situacion A — Es un problema real en el codigo

El hallazgo apunta a algo que de verdad hay que corregir. La solucion es arreglarlo.

**Ejemplos comunes y como corregirlos:**

**Credencial en el codigo** (`no-hardcoded-api-keys`)
```python
# MAL
api_key = "sk-prod-abc123xyz"

# BIEN
import os
api_key = os.getenv("API_KEY")
```

**SQL injection por concatenacion** (`sql-injection-string-concat`)
```python
# MAL
query = "SELECT * FROM users WHERE id = " + user_id
cursor.execute(query)

# BIEN
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

**Debug activado en produccion** (`debug-mode-production`)
```python
# MAL
DEBUG = True

# BIEN
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
```

Haz el cambio, haz push de la rama, y el check se re-ejecuta automaticamente.

---

### Situacion B — Es un falso positivo o codigo de test

El hallazgo apunta a algo que no es un riesgo real: una credencial de fixture de test, un patron en codigo generado automaticamente, un archivo de ejemplo documentado.

En este caso puedes solicitar una excepcion aprobada.

**Proceso para solicitar una excepcion:**

1. Ir al formulario de solicitud:
   [github.com/jgutierrezdtt/security-platform/issues/new?template=exception-request.yml](https://github.com/jgutierrezdtt/security-platform/issues/new?template=exception-request.yml)

2. Rellenar el formulario con:
   - El ID de la regla (lo ves en el comentario del PR, ej: `no-hardcoded-api-keys`)
   - El archivo y ruta exacta
   - Por que crees que es un falso positivo (minimo una explicacion tecnica de 50 caracteres)
   - El tipo: `false_positive`, `test_code`, `generated_code`, `not_used`, o `accepted_risk`

3. El security team revisa en 48 horas laborables

4. Si aprueban la excepcion, la anadir al registro. En el siguiente escaneo de tu PR el hallazgo quedara excluido.

**Mientras esperas la excepcion**, el PR sigue bloqueado. Si es urgente, comunica al security team para priorizar la revision.

---

### Situacion C — Ya existe una excepcion pero sigue bloqueando

Esto puede pasar porque:

- La excepcion esta en `security-exceptions` pero el path del archivo no coincide exactamente con el glob de la excepcion. Verificar con el security team.
- La excepcion ha expirado. Ver la columna `expires_at` en la excepcion.
- El secret `EXCEPTIONS_READER_TOKEN` ha expirado en tu repo. Contactar al security team.

---

## El check de Dependabot tambien falla

Si el bloqueo viene del check de Dependabot y no de Semgrep, el comentario dira algo como:

```
Dependabot Alert Check — Resultados

Estado: BLOQUEADO

Resumen de alertas abiertas
CRITICAL: 2
HIGH: 3
MEDIUM: 1
```

**Que hacer:**

1. Ir a la pestana Security > Dependabot alerts de tu repo
2. Para cada alerta CRITICAL o HIGH: actualizar la dependencia vulnerable a la version que la corrige
3. Si la dependencia no tiene fix disponible aun, solicitar una excepcion temporal al security team explicando que no hay version sin vulnerabilidad

La mayoria de alertas se resuelven actualizando el `package.json`, `go.mod`, `requirements.txt`, etc. y haciendo push.

---

## Mi PR es un hotfix urgente

Si la rama se llama `hotfix/algo`, el security gate cambia automaticamente a modo `report-only`: los hallazgos aparecen en el comentario pero no bloquean el merge.

Despues del hotfix, abre un issue o PR normal para resolver los hallazgos reportados.

---

## Glosario rapido

| Termino | Significado |
|---------|-------------|
| **Hallazgo** | Un patron que Semgrep ha detectado como potencialmente inseguro |
| **Falso positivo** | Un hallazgo que apunta a codigo que no es realmente un riesgo |
| **Excepcion** | Una dispensa aprobada por el security team que hace que Semgrep ignore un hallazgo concreto |
| **Security gate** | La regla que dice "si hay hallazgos HIGH o CRITICAL, el PR no puede mergearse" |
| **SARIF** | Formato estandar de resultados de seguridad. Los hallazgos tambien aparecen en Security > Code Scanning |
| **Provenance SLSA** | Solo relevante en releases, no en PRs de desarrollo |

---

## Contactar al security team

Si tienes dudas sobre un hallazgo concreto o necesitas ayuda:

- Abrir un issue en [security-platform](https://github.com/jgutierrezdtt/security-platform/issues)
- Mencionar `@jgutierrezdtt/security-team` en el comentario del PR

---

## Mas informacion

- [Como gestionar excepciones en detalle](08-exception-management.md)
- [Como funcionan los security gates](09-security-gates.md)
- [Referencia completa del sistema](00-system-reference.md)
- [Ejemplo de app con hallazgos comentados](https://github.com/jgutierrezdtt/security-example-app)
