# Tutorial 05 — SLSA en Pipelines

> **Audiencia**: DevSecOps engineers, Platform engineers  
> **Nivel**: Avanzado  
> **Tiempo estimado**: 90 minutos  
> **Prerrequisitos**: Familiaridad con GitHub Actions y conceptos de supply chain security

---

## ¿Qué es SLSA?

**Supply chain Levels for Software Artifacts (SLSA)** es un framework de seguridad que garantiza la integridad de los artefactos de software a lo largo de su cadena de suministro.

```
Código fuente → Build → Artefacto → Deployment
     ↑               ↑           ↑
  ¿Quién          ¿Cómo?     ¿Es el
  lo escribió?    ¿Dónde?    mismo?
```

SLSA responde estas preguntas con **provenance**: metadatos firmados criptográficamente que describen cómo se construyó un artefacto.

---

## Niveles de SLSA

| Nivel | Garantías | Requisitos clave |
|-------|-----------|-----------------|
| **L1** | Provenance existe | Build genera provenance |
| **L2** | Build por servicio confiable | CI/CD hospedado firma el provenance |
| **L3** | Build aislado y verificable | Build y provenance en jobs separados, firma Sigstore |
| **L4** | Hermético y reproducible | Build completamente hermético (futuro) |

> **jgutierrezdtt apunta a SLSA L3** para todos los releases de producción.

---

## 1. Arquitectura del workflow SLSA L3

El workflow reutilizable [`reusable/slsa-build.yml`](../../.github/workflows/reusable-slsa-build.yml) implementa SLSA L3:

```
Job: build
├── Checkout código (actions/checkout@v4 con hash)
├── Compilar artefacto
├── Calcular SHA256
└── Upload artifact (actions/upload-artifact@v4)
         │
         │ hash del artefacto (base64-subjects)
         ▼
Job: provenance (AISLADO del build)
├── slsa-github-generator (firmado por SLSA Framework)
├── Genera provenance SLSA L3
├── Firma con Sigstore/Cosign (keyless OIDC)
└── Upload provenance artifact
         │
         ▼
Job: verify
├── Download artefacto + provenance
├── slsa-verifier verify-artifact
└── Confirmación criptográfica ✅
```

**¿Por qué importa el aislamiento?** SLSA L3 requiere que el job que genera el provenance esté **completamente separado** del job de build. Si estuvieran juntos, un atacante que comprometa el build podría manipular el provenance.

---

## 2. Uso básico — Aplicación Go

```yaml
# .github/workflows/release.yml en tu repositorio
name: Release with SLSA L3

on:
  release:
    types: [created]

permissions:
  contents: read  # Permisos mínimos en el nivel del workflow

jobs:
  release:
    name: Build & Publish
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-slsa-build.yml@main
    permissions:
      # Estos permisos son necesarios para el job de provenance
      actions: read
      id-token: write    # Para firma OIDC con Sigstore
      contents: write    # Para subir al release
    with:
      artifact-name: "myapp-linux-amd64"
      artifact-path: "bin/myapp"
      build-command: "CGO_ENABLED=0 go build -ldflags='-s -w' -o bin/myapp ./cmd/myapp"
      go-version: "1.22"
      upload-assets: true
```

---

## 3. Uso avanzado — Múltiples plataformas

```yaml
# .github/workflows/release-multi.yml
name: Multi-platform Release with SLSA L3

on:
  release:
    types: [created]

permissions:
  contents: read

jobs:
  build-linux-amd64:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-slsa-build.yml@main
    permissions:
      actions: read
      id-token: write
      contents: write
    with:
      artifact-name: "myapp-linux-amd64"
      artifact-path: "dist/myapp-linux-amd64"
      build-command: |
        GOOS=linux GOARCH=amd64 CGO_ENABLED=0 \
          go build -ldflags='-s -w' -o dist/myapp-linux-amd64 ./cmd/myapp
      go-version: "1.22"

  build-linux-arm64:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-slsa-build.yml@main
    permissions:
      actions: read
      id-token: write
      contents: write
    with:
      artifact-name: "myapp-linux-arm64"
      artifact-path: "dist/myapp-linux-arm64"
      build-command: |
        GOOS=linux GOARCH=arm64 CGO_ENABLED=0 \
          go build -ldflags='-s -w' -o dist/myapp-linux-arm64 ./cmd/myapp
      go-version: "1.22"

  build-windows:
    uses: jgutierrezdtt/security-platform/.github/workflows/reusable-slsa-build.yml@main
    permissions:
      actions: read
      id-token: write
      contents: write
    with:
      artifact-name: "myapp-windows-amd64.exe"
      artifact-path: "dist/myapp-windows-amd64.exe"
      build-command: |
        GOOS=windows GOARCH=amd64 CGO_ENABLED=0 \
          go build -ldflags='-s -w' -o dist/myapp-windows-amd64.exe ./cmd/myapp
      go-version: "1.22"
```

---

## 4. Verificación de artefactos SLSA

Cualquier usuario puede verificar la autenticidad de un artefacto firmado con SLSA:

### 4.1 Instalar slsa-verifier

```bash
# Linux/macOS
curl -sfL -o slsa-verifier \
  "https://github.com/slsa-framework/slsa-verifier/releases/latest/download/slsa-verifier-linux-amd64"
chmod +x slsa-verifier
sudo mv slsa-verifier /usr/local/bin/

# O con Go
go install github.com/slsa-framework/slsa-verifier/v2/cli/slsa-verifier@latest
```

### 4.2 Verificar un artefacto de release

```bash
# Descargar artefacto y provenance del release
gh release download v1.2.3 \
  --repo jgutierrezdtt/mi-repo \
  --pattern "myapp-linux-amd64*"

# Verificar
slsa-verifier verify-artifact \
  --provenance-path myapp-linux-amd64.intoto.jsonl \
  --source-uri github.com/jgutierrezdtt/mi-repo \
  --source-tag v1.2.3 \
  myapp-linux-amd64

# Salida esperada:
# PASSED: SLSA verification passed
```

### 4.3 Verificar en la pipeline del consumidor (antes de desplegar)

```yaml
# .github/workflows/deploy.yml — verificar antes de desplegar
- name: Verify artifact SLSA provenance
  run: |
    slsa-verifier verify-artifact \
      --provenance-path "${{ env.ARTIFACT_NAME }}.intoto.jsonl" \
      --source-uri "github.com/jgutierrezdtt/mi-repo" \
      --source-tag "${{ env.RELEASE_TAG }}" \
      "${{ env.ARTIFACT_NAME }}"
```

---

## 5. Entender el Provenance SLSA

El archivo `.intoto.jsonl` contiene metadatos firmados. Puedes inspeccionarlo:

```bash
# Decodificar el envelope DSSE
cat myapp-linux-amd64.intoto.jsonl | \
  python3 -c "
import sys, json, base64
envelope = json.load(sys.stdin)
payload = base64.b64decode(envelope['payload'])
print(json.dumps(json.loads(payload), indent=2))
"
```

Ejemplo de provenance decodificado:

```json
{
  "_type": "https://in-toto.io/Statement/v0.1",
  "predicateType": "https://slsa.dev/provenance/v0.2",
  "subject": [
    {
      "name": "myapp-linux-amd64",
      "digest": { "sha256": "abc123..." }
    }
  ],
  "predicate": {
    "builder": {
      "id": "https://github.com/slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@refs/tags/v2.0.0"
    },
    "buildType": "https://github.com/slsa-framework/slsa-github-generator/generic@v1",
    "invocation": {
      "configSource": {
        "uri": "git+https://github.com/jgutierrezdtt/mi-repo@refs/tags/v1.2.3",
        "digest": { "sha1": "deadbeef..." },
        "entryPoint": ".github/workflows/release.yml"
      }
    },
    "metadata": {
      "buildInvocationID": "...",
      "buildStartedOn": "2026-05-10T01:00:00Z",
      "completeness": {
        "parameters": true,
        "environment": false,
        "materials": false
      },
      "reproducible": false
    }
  }
}
```

---

## 6. SLSA para imágenes de contenedor

Para imágenes Docker, usa el generador específico:

```yaml
# .github/workflows/docker-release.yml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image: ${{ steps.build.outputs.image }}
      digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4

      - name: Build and push Docker image
        id: build
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/jgutierrezdtt/mi-app:${{ github.sha }}

  provenance:
    needs: [build]
    permissions:
      actions: read
      id-token: write
      packages: write
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v2.0.0
    with:
      image: ${{ needs.build.outputs.image }}
      digest: ${{ needs.build.outputs.digest }}
    secrets:
      registry-username: ${{ github.actor }}
      registry-password: ${{ secrets.GITHUB_TOKEN }}
```

---

## 7. Pinning de acciones (requisito de seguridad)

Para prevenir ataques de supply chain en las propias acciones de GitHub:

```yaml
# ❌ MAL — versión mutable, vulnerable a ataques
- uses: actions/checkout@v4

# ✅ BIEN — hash inmutable, verificable
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
```

Para actualizar hashes automáticamente, usa [Dependabot con `github-actions`](06-dependabot-activation.md).

---

## 8. OpenSSF Scorecard — puntuación de seguridad del repo

```yaml
# .github/workflows/scorecard.yml
name: OpenSSF Scorecard

on:
  schedule:
    - cron: '0 2 * * 1'  # Lunes 02:00 UTC
  push:
    branches: [main]

permissions:
  security-events: write
  id-token: write
  contents: read
  actions: read

jobs:
  scorecard:
    runs-on: ubuntu-latest
    steps:
      - name: Run Scorecard
        uses: ossf/scorecard-action@e38b1902ae4f44df626f11ba0734b14fb91f8f29  # v2.3.3
        with:
          results_file: scorecard.sarif
          results_format: sarif
          publish_results: true

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: scorecard.sarif
          category: scorecard
```

---

## 9. Monitorización y alertas de SLSA

SLSA solo se ejecuta en releases, no en PRs. Eso significa que si falla, no hay nadie mirando activamente el PR — el error puede pasar desapercibido. Esta sección explica cómo detectar fallos y cómo reaccionar.

### 9.1 Dónde aparecen los errores de SLSA

**En GitHub Actions (principal):**

```
Repositorio → Actions → Workflows → "Release with SLSA L3"
```

Si el workflow falla, el release queda creado pero **sin el provenance adjunto**. El artefacto existe, pero no puede ser verificado por los consumidores.

**En el release de GitHub:**

```
Repositorio → Releases → [release concreto]
```

Si el job de provenance falló, el archivo `.intoto.jsonl` no estará entre los assets del release. La ausencia de ese archivo es la señal de fallo.

**Comprobación rápida:**
```bash
# Verificar que el provenance existe en el último release
REPO="jgutierrezdtt/mi-repo"
gh release view --repo "$REPO" \
  --json assets \
  --jq '.assets[].name' | grep -q ".intoto.jsonl" \
  && echo "✅ Provenance presente" \
  || echo "❌ Provenance AUSENTE — el release no tiene SLSA L3"
```

### 9.2 Fallos más comunes y cómo resolverlos

**Fallo 1: Job de provenance falla con "token permissions"**

```
Error: Unhandled error: Error: The ACTIONS_ID_TOKEN_REQUEST_URL is not set
```

Causa: El job de provenance necesita `id-token: write` para firmar con Sigstore.

Solución: En el workflow caller, asegúrate de que el job que llama al generador SLSA tiene este permiso:
```yaml
permissions:
  id-token: write     # Obligatorio para firmar con Sigstore
  contents: write     # Para subir assets al release
  actions: read       # Para leer el workflow del repo
```

---

**Fallo 2: `slsa-github-generator` devuelve "builder not found"**

```
Error: builder not found for: https://github.com/slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v2.0.0
```

Causa: Se usó una versión de `slsa-github-generator` que no existe o cuya firma Sigstore ha cambiado.

Solución: Verifica que la versión en el workflow es válida:
```bash
# Ver las versiones publicadas
gh release list --repo slsa-framework/slsa-github-generator --limit 5
```

Y referencia siempre por tag **y** hash:
```yaml
uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v2.0.0
# Con hash para máxima seguridad:
# uses: slsa-framework/slsa-github-generator/...@a1b2c3d4...
```

---

**Fallo 3: El job de build pasa pero el job de provenance falla silenciosamente**

El release se crea con el artefacto pero sin el `.intoto.jsonl`. El workflow marca el run como "parcialmente fallido" (naranja, no rojo) si el job de provenance tiene `continue-on-error`.

**Importante:** El job de provenance NO debe tener `continue-on-error: true`. Si falla, el pipeline debe fallar.

---

**Fallo 4: `slsa-verifier` rechaza el artefacto en el deployment**

```
FAILED: SLSA verification failed: provenance not found for artifact
```

Causas y soluciones:

| Causa | Diagnóstico | Solución |
|-------|-------------|---------|
| El hash del artefacto no coincide | El binario fue modificado después del build | Descargar de nuevo del release original |
| El provenance es de otro commit | Se reusó un provenance de otro release | Descargar el `.intoto.jsonl` del mismo release |
| `--source-uri` incorrecto | El repo o la rama especificados no coinciden | Usar exactamente `github.com/org/repo` |
| Sigstore timestamp expirado | El provenance tiene más de 90 días y Fulcio cambió | Verificar con `--skip-tlog-verification` (solo para diagnóstico) |

### 9.3 Configurar alertas automáticas cuando un release falla

Por defecto, GitHub no crea una alerta ni un issue si el workflow de release falla. Para detectarlo automáticamente:

**Opción A — Notificación por email (GitHub nativo):**
```
Repositorio → Settings → Notifications → Workflow runs → "Failed workflows only"
```
Esto notifica al repo admin. Suficiente para repos pequeños.

**Opción B — Crear un issue automáticamente cuando el release falla:**

Añadir este job al workflow de release en `security-platform`:
```yaml
  notify-on-failure:
    name: Notify on SLSA failure
    runs-on: ubuntu-latest
    needs: [build, provenance, verify]
    if: failure()
    permissions:
      issues: write
    steps:
      - name: Create issue on SLSA failure
        uses: actions/github-script@v7
        with:
          script: |
            const run_url = `https://github.com/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `[SLSA] Fallo en release ${context.ref} — provenance no generado`,
              body: `## Release sin SLSA L3\n\n` +
                    `El workflow de release falló y el provenance SLSA no se generó.\n\n` +
                    `**Release:** \`${context.ref}\`\n` +
                    `**Run:** ${run_url}\n\n` +
                    `### Impacto\n` +
                    `Los consumidores que verifiquen el artefacto con \`slsa-verifier\` **fallarán**.\n\n` +
                    `### Acción requerida\n` +
                    `1. Revisar el log del run enlazado\n` +
                    `2. Corregir el problema\n` +
                    `3. Crear un nuevo release (no reutilizar el tag existente)`,
              labels: ['security', 'slsa', 'release-failure'],
              assignees: ['security-team']
            });
```

**Opción C — Webhook a Slack/Teams:**

```yaml
  notify-on-failure:
    needs: [build, provenance, verify]
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: slackapi/slack-github-action@v1.26.0
        with:
          payload: |
            {
              "text": "❌ SLSA release fallido en ${{ github.repository }}",
              "blocks": [{
                "type": "section",
                "text": {
                  "type": "mrkdwn",
                  "text": "*❌ Release sin provenance SLSA*\nRepo: `${{ github.repository }}`\nTag: `${{ github.ref_name }}`\n<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|Ver run>"
                }
              }]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK
```

### 9.4 Auditoría periódica — Verificar que todos los releases tienen provenance

El workflow `org-security-report` (lunes 03:00 UTC) puede ampliarse para comprobar si los últimos N releases de cada repo tienen el archivo `.intoto.jsonl`. Si detecta un release sin provenance, lo añade al reporte semanal.

También puedes lanzarlo manualmente:
```bash
# Comprobar los últimos 5 releases de un repo
gh release list --repo jgutierrezdtt/mi-repo --limit 5 --json tagName,assets \
  --jq '.[] | {tag:.tagName, has_provenance: ([.assets[].name | test(".intoto.jsonl")] | any)}'
```

Salida esperada:
```json
{"tag": "v1.3.0", "has_provenance": true}
{"tag": "v1.2.1", "has_provenance": true}
{"tag": "v1.2.0", "has_provenance": false}   ← release problemático
```

### 9.5 Qué hacer si un release ya publicado no tiene provenance

No se puede añadir el provenance a posteriori — el provenance está ligado al run de GitHub Actions que construyó el artefacto, y ese run no se puede repetir para el mismo commit con el mismo resultado firmado.

**Opciones:**

1. **Crear un nuevo release** con el mismo código pero un tag nuevo (ej. `v1.2.0-fixed`). El nuevo run genera un provenance válido.

2. **Documentar en el release** que el provenance está ausente y por qué, para que los consumidores sean conscientes.

3. **Notificar a los consumidores** que ya descargaron ese release, para que vuelvan a descargarlo desde el nuevo tag.

> No elimines el release original si ya fue descargado — los consumidores que intenten verificar el hash del artefacto original necesitan que siga accesible.

---

## 10. Checklist de SLSA

- [ ] **Workflow de build** usa `actions/checkout@v4` con hash pinned
- [ ] **Job de provenance** está separado del job de build
- [ ] **Permisos** mínimos en cada job (`id-token: write` solo donde se necesita)
- [ ] **slsa-github-generator** referenciado por versión y hash
- [ ] **Provenance** subido al release junto con el artefacto
- [ ] **slsa-verifier** integrado en el pipeline de deployment del consumidor
- [ ] **OpenSSF Scorecard** ejecutándose semanalmente
- [ ] **Todas las acciones de terceros** pinned por hash (Dependabot las actualiza)
- [ ] **Alertas de fallo** configuradas (email, issue automático, o Slack)
- [ ] **Verificación periódica** de que todos los releases tienen provenance

---

## Siguiente paso

➡️ [Tutorial 06 — Activación de Dependabot](06-dependabot-activation.md)
