# Referencia del Sistema — Cuando se ejecuta cada proceso y como se reportan los resultados

> Este documento es la referencia unificada del sistema de seguridad.
> Explica que hace cada proceso, cuando se ejecuta, quien lo activa y como aparecen los resultados.
> Los tutoriales individuales entran en detalle de configuracion. Este documento da la vision de conjunto.

---

## Indice

1. [Mapa completo del sistema](#1-mapa-completo-del-sistema)
2. [Tabla de triggers](#2-tabla-de-triggers)
3. [Flujo de un Pull Request](#3-flujo-de-un-pull-request)
4. [Flujo de un Release — SLSA](#4-flujo-de-un-release--slsa)
5. [Procesos automaticos en segundo plano](#5-procesos-automaticos-en-segundo-plano)
6. [Como aparecen los resultados](#6-como-aparecen-los-resultados)
7. [Que cubre SLSA y que no cubre](#7-que-cubre-slsa-y-que-no-cubre)

---

## 1. Mapa completo del sistema

```
                          jgutierrezdtt/security-platform
                         ┌────────────────────────────────┐
                         │  Reglas Semgrep                │
                         │  Umbrales de severidad         │
                         │  Logica de excepciones         │
                         │  Politicas de reporte          │
                         └────────────────┬───────────────┘
                                          │ uses: ...@main
                     ┌────────────────────┼────────────────────┐
                     │                   │                    │
            tu-repo-A/             tu-repo-B/           tu-repo-C/
        .github/workflows/     .github/workflows/   .github/workflows/
          security.yml           security.yml          security.yml
          (15 lineas)            (15 lineas)           (15 lineas)
                     │                   │                    │
                     └────────────────────┼────────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
            semgrep-scan           dependabot-check        slsa-build
            (en cada PR)           (en cada PR)          (en cada release)
                    │                     │
                    └──────────┬──────────┘
                               │ consulta excepciones
                    jgutierrezdtt/security-exceptions
                    (read-only, aprobadas por security-team)
```

---

## 2. Tabla de triggers

Todos los procesos que existen en el sistema, cuando se ejecutan y quien los activa:

| Proceso | Activado por | Cuando | Actua sobre |
|---------|-------------|--------|-------------|
| **Semgrep scan** | GitHub Actions | Cada PR abierto o actualizado | El diff del PR (por defecto) |
| **Semgrep scan completo** | GitHub Actions (schedule) | Lunes 06:00 UTC | Todo el repositorio |
| **Dependabot check** | GitHub Actions | Cada PR abierto o actualizado | Alertas abiertas del repo |
| **Dependabot update** | GitHub / Dependabot | Lunes (configurable) | `package.json`, `go.mod`, etc. |
| **SLSA build + provenance** | GitHub Actions | Al crear un Release o tag `v*.*.*` | El artefacto de release |
| **Validacion de excepciones** | GitHub Actions | Cada PR en security-exceptions | Archivos YAML de excepciones |
| **Alerta de excepciones proximas a expirar** | GitHub Actions (schedule) | Lunes (30 dias antes de expiry) | Excepciones en security-exceptions |
| **Dashboard de org** | GitHub Actions (schedule) | Domingo 02:00 UTC | README de security-platform |
| **Deteccion de repos sin configurar** | GitHub Actions (schedule) | Lunes 08:00 UTC | Todos los repos de la org |

---

## 3. Flujo de un Pull Request

Este es el camino que recorre cada PR desde que se abre hasta que se puede mergear:

```
Developer hace push a una rama
              │
              ▼
    GitHub crea o actualiza el PR
              │
              ▼
    ┌─────────────────────────────┐
    │   security.yml se dispara   │
    │   (trigger: pull_request)   │
    └──────────┬──────────────────┘
               │
      ┌────────┴────────┐
      │                 │
      ▼                 ▼
  semgrep           dependabot
  (job)             (job)
      │                 │
      │                 │
      ▼                 │
 Descarga excepciones   │
 de security-exceptions │
      │                 │
      ▼                 ▼
 Ejecuta semgrep    Llama a GitHub API
 sobre el diff      /repos/.../dependabot/alerts
      │                 │
      ▼                 ▼
 Filtra hallazgos   Cuenta alertas
 con excepciones    por severidad
 aprobadas          │
      │                 │
      ▼                 ▼
 ┌──────────────────────────────────┐
 │  Genera comentario sticky en PR  │
 │  (se actualiza, no se duplica)   │
 └──────────────────────────────────┘
      │                 │
      ▼                 ▼
 ¿Hallazgo HIGH    ¿Alertas CRITICAL
 o CRITICAL sin    o HIGH sin resolver?
 excepcion?        │
      │             │
     Si            Si
      └──────┬──────┘
             │
             ▼
     Check falla — el PR
     NO puede mergearse
     (branch protection)
             │
            No  ←── Developer corrige o
             │        solicita excepcion
             ▼
     Check pasa — PR se puede
     revisar y mergear
```

### Que pasa si hay un hotfix urgente

Si la rama se llama `hotfix/*`, el security gate cambia automaticamente a modo `report-only`: los hallazgos se reportan en el PR pero no bloquean el merge. Esto permite actuar rapidamente en produccion. El hallazgo queda registrado para resolverse en el siguiente PR normal.

---

## 4. Flujo de un Release — SLSA

SLSA solo se ejecuta cuando se crea un Release en GitHub (o se hace push de un tag `v*.*.*`). No interfiere con el desarrollo diario.

```
Security team o release manager
crea un Release en GitHub
(o hace git tag v1.2.3 && git push --tags)
              │
              ▼
    ┌───────────────────────────────────┐
    │   release.yml se dispara          │
    │   (trigger: release: published)   │
    └────────────────┬──────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     │
    Job: build                  │
    ─────────────               │
    Checkout del codigo         │
    Ejecuta el build command    │
    (go build / npm run build   │
     / python setup.py build)   │
    Calcula SHA-256             │
    Sube artefacto              │
    (upload-artifact@v4)        │
          │                     │
          │ hash del artefacto  │
          ▼                     │
    Job: provenance             │
    ──────────────              │
    AISLADO del build job       │
    (no puede ser influenciado) │
    slsa-github-generator       │
    (firmado por SLSA Framework)│
    Genera provenance.intoto    │
    Firma con Sigstore keyless  │
    (sin clave privada local)   │
    Sube provenance al Release  │
          │                     │
          └──────────┬──────────┘
                     │
                     ▼
    Job: verify
    ───────────
    Descarga artefacto + provenance
    slsa-verifier verify-artifact
    Verifica que:
    - La firma es de Sigstore
    - El builder es GitHub Actions
    - El workflow es el correcto
    - El repo y la rama coinciden
              │
              ▼
    Si la verificacion falla → el job falla
    y el Release no es confiable

    Si pasa → el artefacto tiene provenance
    SLSA L3 adjunto al Release de GitHub
```

### Como verificar un artefacto externamente

Cualquier persona que descargue el artefacto puede verificar su autenticidad:

```bash
# Descargar el artefacto y su provenance
gh release download v1.2.3 \
  --repo jgutierrezdtt/tu-repo \
  --pattern "*.tar.gz" \
  --pattern "*.intoto.jsonl"

# Verificar
slsa-verifier verify-artifact mi-artefacto.tar.gz \
  --provenance-path mi-artefacto.tar.gz.intoto.jsonl \
  --source-uri github.com/jgutierrezdtt/tu-repo \
  --source-tag v1.2.3
```

---

## 5. Procesos automaticos en segundo plano

Estos procesos no requieren ningun PR. Se ejecutan solos segun el calendario y crean GitHub Issues o actualizan el README cuando encuentran algo.

### Calendario semanal

```
Lunes 06:00 UTC
    │
    ├── Semgrep scan completo de todos los repos monitorizados
    │   (detecta problemas en codigo que no ha pasado por PR recientemente)
    │
    ├── Deteccion de repos sin security.yml
    │   ─────────────────────────────────
    │   Lista todos los repos de la org
    │   Filtra los que no tienen .github/workflows/security.yml
    │   Si encuentra alguno → crea GitHub Issue en security-platform
    │   Asigna al security-team para que actuen
    │
    └── Validacion de excepciones proximas a expirar
        ─────────────────────────────────────────────
        Lee todos los YAML en security-exceptions
        Calcula dias hasta expires_at
        Si alguna expira en menos de 30 dias → crea GitHub Issue
        Asigna al security-team para renovar o revocar

Domingo 02:00 UTC
    │
    └── Dashboard de seguridad de la org
        ──────────────────────────────────
        Llama a GitHub API por cada repo en config/monitored-repos.txt
        Recoge: alertas Dependabot, alertas Code Scanning, estado Secret Scanning
        Actualiza la tabla del README de security-platform
        Hace commit con [skip ci] para no lanzar pipelines
```

---

## 6. Como aparecen los resultados

Hay cuatro canales por los que el sistema comunica resultados. Cada uno tiene un proposito distinto:

### Canal 1: Comentario sticky en el PR

**Quien lo ve**: El developer que abrio el PR y sus revisores.
**Cuando aparece**: A los pocos minutos de abrir o actualizar el PR.
**Que contiene**:

```
Semgrep Security Scan — Resultados

Repositorio: jgutierrezdtt/tu-repo | Rama: feature/login | Commit: a1b2c3d4

Estado: BLOQUEADO — Vulnerabilidades Altas

Resumen
Criticas | Altas | Medias | Bajas | Info | Exceptuadas
   0     |   2   |   3    |   1   |  0   |     1

Hallazgos Activos
# | Severidad | Regla                      | Archivo          | Linea
1 | HIGH      | sql-injection-string-concat | src/db/queries.py | 45
2 | HIGH      | no-hardcoded-api-keys       | config/settings.py | 12
3 | MEDIUM    | debug-mode-production       | .env               | 3

Para solicitar una excepcion: [enlace al formulario]
```

El comentario se actualiza en cada push. No se crean comentarios nuevos — siempre es el mismo, con los datos actualizados.

### Canal 2: Check de GitHub (status check)

**Quien lo ve**: Cualquiera que mire el PR — aparece en la lista de checks.
**Cuando aparece**: Junto con el comentario.
**Que contiene**: Un estado simple — verde (pasa) o rojo (falla) — con un enlace al log detallado.
**Efecto en el merge**: Si el check falla y la rama tiene branch protection configurada, el boton de merge queda deshabilitado.

### Canal 3: Job Summary (pestana Actions)

**Quien lo ve**: El developer, el security team — cualquiera con acceso al repo.
**Cuando aparece**: Al finalizar el workflow.
**Que contiene**: Tabla resumen con metricas del analisis (archivos analizados, reglas aplicadas, tiempo, hallazgos por severidad) y enlace al artefacto JSON completo.

### Canal 4: Security tab de GitHub (SARIF)

**Quien lo ve**: El security team — pestana "Security > Code Scanning".
**Cuando aparece**: Despues de cada scan que sube SARIF.
**Que contiene**: Todos los hallazgos con contexto, historial, severidad CVSS, y estado (open/fixed/dismissed). Permite hacer seguimiento de hallazgos a lo largo del tiempo aunque cambien entre commits.
**Ventaja**: Los hallazgos que se corrigen en un PR se marcan automaticamente como "Fixed" sin ningun paso manual.

### Canal 5: GitHub Issues (procesos automaticos)

**Quien lo ve**: El security-team (asignado en el issue).
**Cuando aparece**: Solo en casos que requieren accion humana:
- Repo detectado sin `security.yml`
- Excepcion proxima a expirar
- Error critico en el workflow de validacion

---

## 7. Que cubre SLSA y que no cubre

SLSA (Supply chain Levels for Software Artifacts) responde a una pregunta muy especifica: **¿este artefacto fue construido exactamente con este codigo, por este pipeline, sin que nadie lo haya modificado por el camino?**

### Lo que SLSA L3 garantiza

| Garantia | Como la verifica SLSA |
|----------|-----------------------|
| El artefacto viene del codigo que dice venir | El provenance incluye el SHA exacto del commit usado en el build |
| El build lo hizo GitHub Actions, no alguien manualmente | La firma es de Sigstore y solo GitHub puede crearla |
| El workflow de build no fue modificado durante la ejecucion | El job de provenance corre en un job separado, aislado |
| Nadie reemplazo el artefacto despues del build | El hash SHA-256 del artefacto esta firmado en el provenance |
| La firma es verificable sin depender de una clave privada | Sigstore usa el OIDC de GitHub como identidad, no un secreto |

### Lo que SLSA NO garantiza

| Lo que no cubre | Que herramienta lo cubre |
|-----------------|--------------------------|
| Vulnerabilidades en el codigo | Semgrep, CodeQL |
| Dependencias vulnerables | Dependabot |
| Secretos en el codigo | Secret Scanning |
| El codigo hace lo que dice hacer | Tests, revision de codigo |
| La imagen Docker base es segura | Trivy, Docker Scout |
| Los permisos en produccion son correctos | IAM reviews, politicas de org |

### Cuando es util SLSA en la practica

SLSA no es util para el desarrollo diario — no aparece en PRs ni en feature branches. Es util en dos escenarios:

**Escenario 1: Distribucion de artefactos**
Cuando distribuyes un binario, una libreria o un paquete a otros equipos o usuarios externos, el provenance SLSA les permite verificar que lo que estan usando es exactamente lo que tu construiste.

**Escenario 2: Auditoria post-incidente**
Si se descubre que un artefacto fue comprometido (un ataque de supply chain), el provenance permite reconstruir exactamente que codigo, que dependencias y que pipeline produjeron ese artefacto.

### Relacion entre SLSA y los otros procesos

```
Desarrollo (diario)          Release (puntual)

   Semgrep ──────────────── El codigo que llega al release
   Dependabot ──────────── ya paso por todos estos checks
   Secret Scanning ────────         │
                                     ▼
                              SLSA Build
                              Garantiza que el artefacto
                              viene exactamente de ese
                              codigo ya verificado
```

SLSA no sustituye a Semgrep ni a Dependabot — los complementa. Son capas distintas: los checks de PR verifican la calidad del codigo, SLSA verifica la integridad del artefacto final.

---

## Referencias rapidas

| Quiero saber... | Ir a... |
|-----------------|---------|
| Como configurar Semgrep | [Tutorial 07](07-semgrep-activation.md) |
| Como gestionar excepciones | [Tutorial 08](08-exception-management.md) |
| Como configurar los security gates | [Tutorial 09](09-security-gates.md) |
| Como leer el dashboard de reporting | [Tutorial 10](10-reporting.md) |
| Como activar SLSA en un release | [Tutorial 05](05-slsa-pipelines.md) |
| Como integrar un repo nuevo | [security-consumer-template](https://github.com/jgutierrezdtt/security-consumer-template) |
| Ver un ejemplo funcional | [security-example-app](https://github.com/jgutierrezdtt/security-example-app) |
