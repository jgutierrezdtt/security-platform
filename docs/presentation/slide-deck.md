# Deck: Security Platform — amazing-protection
## Guía de slides para presentación

**Audiencia:** Equipos de desarrollo + Tech Leads  
**Duración estimada:** 35–45 min  
**Objetivo:** Explicar el sistema, por qué existe y cómo adoptarlo

---

## BLOQUE 1 — El problema
*Slides 1–4 · ~5 min*

---

### Slide 1 — Portada
**Título:** Seguridad sin fricciones  
**Subtítulo:** El Security Platform de amazing-protection  
**Visual:** Logo organización + iconos de shield / pipeline  
**Pie:** amazing-protection · Mayo 2026

---

### Slide 2 — El estado actual (antes)
**Título:** ¿Dónde estamos hoy?

**Contenido (3 columnas):**
| Sin estándar | Sin visibilidad | Sin escala |
|---|---|---|
| Cada repo configura la seguridad a su manera (o no la configura) | No hay visión global de vulnerabilidades en la org | 200 repos, cada mejora hay que aplicarla manualmente 200 veces |

**Nota al pie:** El mismo hallazgo se trata de forma diferente en cada equipo.

---

### Slide 3 — El coste real
**Título:** ¿Cuánto nos cuesta no tenerlo?

**Bullets:**
- Una vulnerabilidad crítica descubierta en producción cuesta 10–100x más que en desarrollo
- Sin security gate: los PRs se mergean sin revisión de seguridad
- Sin trazabilidad: no podemos demostrar compliance ante una auditoría
- Sin excepciones gestionadas: los equipos desactivan las herramientas porque "molestan demasiado"

**Visual:** Iceberg — lo visible (el bug) vs lo oculto (el coste)

---

### Slide 4 — La propuesta
**Título:** Una plataforma, adoptada por todos

**Frase central:**  
> "Que la seguridad sea una consecuencia automática de trabajar en amazing-protection, no un esfuerzo extra."

**3 principios:**
1. **Centralizado** — las reglas se definen una vez, se aplican en todos los repos
2. **No bloqueante por defecto** — modo `report-only` para adopción gradual
3. **Escalable** — un PR de onboarding por repo, listo para mergear

---

## BLOQUE 2 — Arquitectura del sistema
*Slides 5–9 · ~10 min*

---

### Slide 5 — Los dos repositorios
**Título:** Hub & Spoke: dos repos que gobiernan todo

**Diagrama (dos cajas):**

```
┌─────────────────────────────┐    ┌──────────────────────────────┐
│    security-platform        │    │    security-exceptions        │
│                             │    │                               │
│  • Workflows reutilizables  │    │  • Registro de excepciones    │
│  • Reglas Semgrep           │    │    aprobadas                  │
│  • Tutoriales (10 guías)    │    │  • Falsos positivos globales  │
│  • Templates consumer       │    │  • Excepciones por repo       │
│  • Dashboard de la org      │    │  • Acceso read-only           │
└─────────────────────────────┘    └──────────────────────────────┘
             ↕                                   ↕
         200 repos consumer (lectores)
```

**Nota:** Los repos consumer solo LLAMAN a los workflows. No copian código de seguridad.

---

### Slide 6 — Cómo fluye un PR en un repo consumer
**Título:** Lo que ocurre cuando un desarrollador abre un PR

**Diagrama de flujo (izquierda → derecha):**

```
Developer abre PR
      ↓
Workflow security.yml se activa
      ↓
        ┌──────────────────────────────┐
        │  Semgrep escanea el diff     │
        │  Descarga excepciones        │
        │  Filtra falsos positivos     │
        │  Genera tabla de hallazgos   │
        └──────────────────────────────┘
      ↓
      ┌──────────────────────────────┐
      │  Dependabot check            │
      │  Cuenta alertas abiertas     │
      │  Verifica config presente    │
      └──────────────────────────────┘
      ↓
Security Summary Job
      ↓
   ¿Hay CRITICAL o HIGH sin excepción?
      ↓               ↓
    SÍ → ❌           NO → ✅
  PR bloqueado      PR puede mergearse
```

---

### Slide 7 — Lo que ve el desarrollador
**Título:** Sin salir del PR

**2 columnas:**

**Columna izquierda — Comentario sticky en el PR:**
- Tabla con hallazgos de Semgrep (severidad, regla, archivo, línea)
- Estado de Dependabot (alertas abiertas por severidad)
- Resumen final: ✅ / ❌

**Columna derecha — Job Summary (Actions tab):**
- Misma información, con más detalle
- SARIF subido al Security tab de GitHub
- Artefactos descargables (JSON + SARIF)

**Mensaje clave:** El desarrollador recibe feedback inmediato, en contexto, sin herramientas externas.

---

### Slide 8 — SLSA: la cadena de suministro
**Título:** Cada artefacto firmado y verificable

**Contenido:**
- **¿Qué es SLSA?** — Supply chain Levels for Software Artifacts (framework de Google/Linux Foundation)
- **¿Qué conseguimos?** — Cada release tiene un documento de procedencia firmado digitalmente
- **¿Qué garantiza?** — El artefacto fue construido exactamente en ese commit, con ese workflow, en GitHub Actions

**Tabla niveles:**
| Nivel | Garantía | Nosotros |
|-------|----------|----------|
| SLSA 1 | Build documentado | ✅ |
| SLSA 2 | Build en CI firmado | ✅ |
| **SLSA 3** | **Build aislado + provenance verificable** | ✅ Objetivo |

**Nota:** No requiere infraestructura propia — usa el generador oficial de SLSA Framework + Sigstore.

---

### Slide 9 — El repositorio de excepciones
**Título:** Gestionar lo que no podemos corregir hoy

**Problema que resuelve:**
> "Semgrep me encuentra algo en código legacy que no puedo corregir ahora. ¿Qué hago?"

**Flujo (4 pasos):**
1. Desarrollador abre issue en `security-platform` con el formulario de excepción
2. Security team revisa y aprueba (o rechaza) el PR a `security-exceptions`
3. La excepción tiene **fecha de expiración** (máximo 1 año)
4. El workflow de Semgrep la descarga automáticamente y filtra el hallazgo

**Puntos clave:**
- Solo el security-team puede añadir excepciones (CODEOWNERS + Branch Protection)
- Las excepciones expiradas **se detectan automáticamente** y se abre un issue
- Hay excepciones globales (para toda la org) y por repositorio

---

## BLOQUE 3 — Seguridad de la plataforma misma
*Slides 10–12 · ~7 min*

---

### Slide 10 — Roles y control de acceso
**Título:** Quién puede hacer qué

**Tabla:**
| Rol | Puede | No puede |
|-----|-------|----------|
| **Developer** | Llamar a los workflows, abrir issues de excepción | Modificar los workflows, añadir excepciones |
| **Platform Team** | Modificar templates, tutoriales | Modificar reglas de Semgrep sin security-team |
| **Security Team** | Todo — único que aprueba PRs en security-platform | — |

**Visual:** 3 círculos concéntricos (Developer → Platform → Security)

**Nota:** El acceso se gobierna con CODEOWNERS + Branch Protection, no con confianza implícita.

---

### Slide 11 — Protección de ramas y aprobaciones
**Título:** Doble control donde más importa

**Reglas aplicadas en `security-platform`:**
- `main` requiere **2 aprobaciones** de `security-team` para `.github/workflows/reusable/`
- No se puede hacer push directo a `main`
- No se permite self-merge
- Los checks de CI deben pasar antes de mergear

**¿Por qué importa?**
> Un atacante que modificara un workflow reutilizable podría afectar a 200 repos a la vez. El doble control lo previene.

**Equivalente en el mundo físico:** Regla de los dos ojos para operaciones críticas en banca.

---

### Slide 12 — Dependabot y Scorecard en la propia plataforma
**Título:** La plataforma se escanea a sí misma

**Lo que ocurre:**
- Dependabot actualiza las actions con versiones seguras (semanalmente)
- El CI de `security-platform` ejecuta Semgrep sobre sus propios workflows y scripts
- OpenSSF Scorecard evalúa la postura de seguridad del repo (branch protection, pinning, etc.)
- El resultado aparece en el README como badge público

**Mensaje:** No pedimos a los equipos lo que nosotros mismos no hacemos.

---

## BLOQUE 4 — Adopción y escala
*Slides 13–16 · ~8 min*

---

### Slide 13 — Cómo adoptar (para un repo individual)
**Título:** Onboarding de un repo en ~30 minutos

**Timeline visual (línea horizontal):**

```
0 min          5 min             15 min           30 min
  │               │                  │               │
Copiar         Configurar         Primer PR        ✅ Activo
templates      secretos           con escaneo
```

**Los 3 secretos necesarios:**
1. `EXCEPTIONS_READER_TOKEN` — acceso read-only al repo de excepciones
2. `SEMGREP_APP_TOKEN` — (opcional) para Semgrep Cloud Platform
3. `DEPENDABOT_CHECK_TOKEN` — para leer alertas de Dependabot

---

### Slide 14 — Modo report-only
**Título:** Adopción gradual sin romper nada

**¿Qué es?**
> El pipeline ejecuta todos los análisis y genera los reportes, pero **no bloquea el PR**, aunque haya vulnerabilidades.

**Cuándo usarlo:**
- Repos legacy con deuda técnica acumulada
- Proyectos en fase de migración
- Durante la primera semana de adopción (para calibrar)

**Cómo activarlo:**
- Input `report-only: true` en el workflow call
- El PR muestra el comentario con hallazgos pero el check pasa en verde

**Progresión recomendada:**
```
Semana 1-2: report-only → Semana 3-4: bloquear CRITICAL → Mes 2: bloquear HIGH
```

---

### Slide 15 — Escalar a 200 repos
**Título:** Onboarding masivo: de 0 a 200 en un día

**El proceso:**
1. El security team ejecuta `bulk-onboard.py`
2. El script abre **un PR en cada repo** con todos los archivos configurados
3. Cada equipo revisa y mergea su PR cuando esté listo
4. El script actualiza automáticamente el dashboard de la org

**No es big bang:** Cada equipo mergea a su ritmo. El PR ya está listo — solo hay que aprobarlo.

**Detección de nuevos repos:**
- Cada lunes, el workflow `detect-unconfigured-repos` escanea la org
- Si detecta repos sin configurar → crea un issue automático asignado al security team
- Los repos nuevos nunca quedan "fuera del radar"

---

### Slide 16 — El dashboard de la organización
**Título:** Visión global en tiempo real

**Visual (tabla de ejemplo):**

| Repositorio | Estado | Semgrep | Dependabot | Secrets |
|-------------|--------|---------|------------|---------|
| frontend-app | ✅ | 🟢 C:0 H:0 | 🟢 C:0 H:0 | ✅ 0 |
| backend-api | ✅ | 🟠 C:0 H:2 | 🟢 C:0 H:0 | ✅ 0 |
| payments-service | ✅ | 🔴 C:1 H:0 | 🟠 C:0 H:3 | ⚠️ 1 |
| legacy-portal | ⚠️ report-only | 🟠 C:0 H:5 | 🔴 C:2 H:1 | ✅ 0 |

**Dónde vive:** En el README de `security-platform`, actualizado cada domingo por el workflow `org-security-report`.

**Quién puede verlo:** Cualquier miembro de la organización con acceso al repo.

---

## BLOQUE 5 — Gestión continua
*Slides 17–19 · ~5 min*

---

### Slide 17 — Ciclo de vida de una excepción
**Título:** Las excepciones no son para siempre

**Diagrama circular:**
```
Hallazgo en PR
     ↓
Issue de excepción (formulario)
     ↓
Revisión security team (48h)
     ↓
PR aprobado → excepción activa (máx 1 año)
     ↓
30 días antes de expirar → Issue automático de renovación
     ↓
¿Se puede corregir ya? → SÍ: fix en código / NO: renovar con nueva justificación
```

**Tipos de excepción:**
- `false_positive` — la regla se equivoca
- `not_used` — el código no llega a producción
- `accepted_risk` — riesgo conocido y asumido explícitamente
- `test_code` — solo en tests
- `generated_code` — código autogenerado

---

### Slide 18 — Gestión de reglas de Semgrep
**Título:** Las reglas son código — se revisan como código

**Dónde viven:** `config/semgrep/rules.yml` en `security-platform`

**Proceso para añadir una regla:**
1. PR con la nueva regla + casos de test documentados
2. Revisión del security team
3. La regla se aplica automáticamente a todos los repos

**Reglas propias vs reglas de la comunidad:**
| Tipo | Mantenimiento | Cuándo usar |
|------|--------------|-------------|
| Reglas propias (en el repo) | Nosotros | Patrones específicos de nuestro stack |
| Reglas de Semgrep (`p/owasp-top-ten`, etc.) | Semgrep community | OWASP, vulnerabilidades conocidas |
| Semgrep Cloud Platform | Semgrep Inc. | Con SEMGREP_APP_TOKEN — analytics + gestión UI |

---

### Slide 19 — El equipo de seguridad como enabler
**Título:** Security team: de gatekeeper a enabler

**Antes:**
- El equipo de seguridad revisa PRs manualmente
- Los equipos esperan feedback
- La seguridad es un cuello de botella

**Después:**
- El feedback es automático e instantáneo (en el mismo PR)
- El security team define las reglas una vez
- El security team revisa excepciones, no cada línea de código
- Los equipos tienen autonomía dentro de los límites definidos

**Métrica clave:** Tiempo entre apertura del PR y feedback de seguridad: de días a minutos.

---

## BLOQUE 6 — Cierre
*Slides 20–21 · ~3 min*

---

### Slide 20 — Resumen: qué tenemos
**Título:** Lo que queda listo hoy

**4 cuadrantes:**

| Gobernanza | Herramientas |
|------------|-------------|
| 10 tutoriales técnicos | Semgrep con excepciones gestionadas |
| Roles y CODEOWNERS definidos | Dependabot activo en todos los repos |
| Proceso de aprobación de PRs | SLSA Level 3 para releases |
| Proceso de excepciones auditado | Dashboard automático de la org |

| Escala | Mantenimiento |
|--------|--------------|
| Onboarding de 200 repos en 1 día | Detección automática de repos nuevos |
| Templates listos para copiar | Excepciones con expiración automática |
| 1 PR por repo, el equipo decide cuándo mergear | La plataforma se escanea a sí misma |

---

### Slide 21 — Próximos pasos
**Título:** ¿Qué hacemos la próxima semana?

**Para el security team:**
1. Revisar y ajustar las reglas de Semgrep propias
2. Ejecutar el onboarding masivo en modo `--dry-run` para validar
3. Definir el SLA de respuesta a excepciones (recomendado: 48h laborables)

**Para los tech leads:**
1. Revisar el PR de onboarding cuando llegue a su repo
2. Identificar código legacy que necesitará excepciones
3. Plantear al equipo la progresión: `report-only → critical → high`

**Para todos:**
1. Leer el ONBOARDING.md (~30 min, paso a paso)
2. Preguntas y excepciones: via issue en `security-platform`

---

## APÉNDICE — Slides de respaldo

---

### Slide A1 — FAQ: ¿Qué pasa si Semgrep bloquea un hotfix urgente?
**Opciones disponibles:**
1. Si es un falso positivo: añadir `# nosemgrep: rule-id` en la línea con justificación en comentario
2. Si es un riesgo real pero el hotfix es urgente: usar `report-only: true` temporalmente y crear la excepción
3. En casos extremos: el security team puede aprobar un bypass documentado en el issue

**Nota importante:** El bypass siempre queda registrado. No hay "saltarse" el proceso sin trazabilidad.

---

### Slide A2 — FAQ: ¿Afecta al rendimiento del pipeline?
**Tiempos aproximados:**
| Step | Tiempo |
|------|--------|
| Semgrep (diff, repo mediano) | 30–90 segundos |
| Semgrep (full scan) | 2–5 minutos |
| Dependabot check | 15–30 segundos |
| SLSA provenance (solo en release) | 3–5 minutos |

**Total para un PR normal:** < 2 minutos en paralelo

---

### Slide A3 — FAQ: ¿Qué ocurre con repos en otros lenguajes?
**Semgrep soporta:** Python, JavaScript/TypeScript, Java, Go, Ruby, PHP, C/C++, Kotlin, Scala, etc.

**Las reglas se ajustan por lenguaje** — Semgrep detecta el lenguaje automáticamente.

**Para lenguajes no soportados:** El workflow pasa en verde (sin hallazgos). Se puede excluir del scope con `.semgrepignore`.

---

### Slide A4 — Glosario
| Término | Significado |
|---------|-------------|
| GHAS | GitHub Advanced Security — suite de herramientas de seguridad de GitHub |
| SARIF | Static Analysis Results Interchange Format — formato estándar para resultados de análisis |
| SLSA | Supply chain Levels for Software Artifacts — framework de seguridad de cadena de suministro |
| SAST | Static Application Security Testing — análisis estático de código fuente |
| Security Gate | Check de CI que bloquea el merge si hay vulnerabilidades por encima del umbral |
| Reusable Workflow | Workflow de GitHub Actions que puede ser llamado desde otros repositorios |
| Fine-grained PAT | Personal Access Token con permisos granulares por repositorio |
| Provenance | Documento firmado que certifica el origen y proceso de construcción de un artefacto |
