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

> **Amazing-protection apunta a SLSA L3** para todos los releases de producción.

---

## 1. Arquitectura del workflow SLSA L3

El workflow reutilizable [`reusable/slsa-build.yml`](../../.github/workflows/reusable/slsa-build.yml) implementa SLSA L3:

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
    uses: amazing-protection/security-platform/.github/workflows/reusable/slsa-build.yml@main
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
    uses: amazing-protection/security-platform/.github/workflows/reusable/slsa-build.yml@main
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
    uses: amazing-protection/security-platform/.github/workflows/reusable/slsa-build.yml@main
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
    uses: amazing-protection/security-platform/.github/workflows/reusable/slsa-build.yml@main
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
  --repo amazing-protection/mi-repo \
  --pattern "myapp-linux-amd64*"

# Verificar
slsa-verifier verify-artifact \
  --provenance-path myapp-linux-amd64.intoto.jsonl \
  --source-uri github.com/amazing-protection/mi-repo \
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
      --source-uri "github.com/amazing-protection/mi-repo" \
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
        "uri": "git+https://github.com/amazing-protection/mi-repo@refs/tags/v1.2.3",
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
          tags: ghcr.io/amazing-protection/mi-app:${{ github.sha }}

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

## 9. Checklist de SLSA

- [ ] **Workflow de build** usa `actions/checkout@v4` con hash pinned
- [ ] **Job de provenance** está separado del job de build
- [ ] **Permisos** mínimos en cada job (`id-token: write` solo donde se necesita)
- [ ] **slsa-github-generator** referenciado por versión y hash
- [ ] **Provenance** subido al release junto con el artefacto
- [ ] **slsa-verifier** integrado en el pipeline de deployment del consumidor
- [ ] **OpenSSF Scorecard** ejecutándose semanalmente
- [ ] **Todas las acciones de terceros** pinned por hash (Dependabot las actualiza)

---

## Siguiente paso

➡️ [Tutorial 06 — Activación de Dependabot](06-dependabot-activation.md)
