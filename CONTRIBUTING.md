# Contributing — security-platform

> **Solo el security-team y el platform-team pueden contribuir directamente a este repositorio.**

---

## Cómo contribuir

### 1. Añadir o modificar reglas de Semgrep

1. Escribe la regla en YAML con el [formato de Semgrep](https://semgrep.dev/docs/writing-rules/rule-syntax/)
2. Prueba la regla localmente: `semgrep --config config/semgrep/rules.yml <directorio>`
3. Añade al menos 1 caso válido y 1 caso de falso positivo esperado en los metadatos
4. Abre un PR con:
   - Descripción del patrón detectado
   - Ejemplos de código vulnerable y correcto
   - Referencia a CWE/OWASP si aplica

### 2. Modificar reusable workflows

Los workflows en `.github/workflows/reusable/` afectan a **todos los repos** que los consumen.

- Siempre incrementar la versión de acciones en `@vX.Y.Z`, nunca usar `@main`
- Documentar los nuevos inputs/outputs/secrets en la cabecera del workflow
- Actualizar `README.md` con los cambios de interface
- Probar el cambio en un repo de test antes de mergear a `main`

### 3. Actualizar templates de consumer

Los templates en `templates/consumer/` son la primera experiencia de los nuevos repos.

- Mantener los comentarios explicativos en el YAML
- Verificar que el ONBOARDING.md refleja los cambios

### 4. Añadir un tutorial

Los tutoriales van en `docs/tutorials/` con el prefijo numérico correspondiente.

- Seguir la estructura: introducción → conceptos → implementación paso a paso → verificación → troubleshooting
- Incluir comandos `gh api` ejecutables, no solo capturas de pantalla
- Añadir al índice en `README.md`

---

## Proceso de PR

1. El PR requiere **2 aprobaciones** del `security-team` para archivos en `.github/workflows/reusable/`
2. El PR requiere **1 aprobación** para el resto de archivos
3. Los checks de CI deben pasar (Semgrep + Dependabot)
4. No se permite self-merge

---

## Estilo de código

- Python: PEP 8, sin librerías externas a menos que sean estrictamente necesarias
- YAML: 2 espacios de indentación, comentarios en castellano
- Markdown: 80 caracteres de ancho máximo (excepto tablas y bloques de código)
