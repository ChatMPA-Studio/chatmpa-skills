---
# ════════════════════════════════════════════════════════════════════════════
# TEMPLETE DE SKILL SERVICE-CONTRACT (servicio de skills de ChatMPA)
#
# Copiar esta carpeta a <nombre-de-la-skill>/ y reemplazar todo lo que está
# entre [corchetes]. Los comentarios con «#» explican cada campo: se pueden
# borrar en la skill final, salvo los que justifican una decisión de método
# (qué se empuja al MCP, por qué ese comparable_value).
#
# Lo leen dos máquinas y un humano:
#   - el orquestador (selección y llamada): name, description, description_es,
#     inputs, acquire.provider;
#   - el servicio de skills (chat-mpa/ChatMPASkills/R/contract.R): todo el
#     front-matter y las secciones «## » del cuerpo;
#   - la revisión humana: el cuerpo.
# Los títulos de sección «## » del cuerpo son fijos: el arnés de validación
# busca «## Random controls» y «## Method (fixed, no degrees of freedom)»
# por su texto exacto.
#
# Vocabulario: las skills NUEVAS usan el vocabulario estándar de contratos
# (opción C, Docs ChatMPA/Vocabulario_Contratos_ChatMPA_borrador.docx):
# nombre genérico en inglés, sin sufijo _filter, rangos con _from/_to. La
# traducción al parámetro real de la tool va en acquire[].provider.params.
# ════════════════════════════════════════════════════════════════════════════

# ── Identidad ───────────────────────────────────────────────────────────────
name: skill-name                 # kebab-case; IGUAL al nombre del directorio
version: 0.1.0                   # semver. Viaja con cada resultado: es como se
                                 # cita un número. patch = texto/corrección sin
                                 # cambio de resultado; minor = cambio compatible;
                                 # major = cambia inputs, salida o método.
tier: 1                          # 0 = sólo datos · 1 = determinista rápida ·
                                 # 2 = bootstrap o modelo (techo de tiempo alto)

# ── Selección (lo lee el modelo a ciegas) ───────────────────────────────────
description: >
  [EN, ≥ 40 caracteres. Qué pregunta del usuario dispara la skill, en lenguaje
  natural, y qué devuelve (valor, categoría, serie). Mencionar la unidad de
  análisis (AMP, región, arrecife, oficina de desembarque) y la base de datos.
  Buen ejemplo: "Assess the trophic health of a reef and answer whether it is
  healthy, degraded, or recovering". Mal ejemplo: "Compute the NRSI".]
description_es:
  # LISTA de frases en español. Cada una se embebe POR SEPARADO y gana la de
  # mejor puntaje contra la pregunta. Reglas:
  #   - la primera: reescritura natural de `description` (no traducción literal);
  #   - las siguientes: UNA frase por tipo de pregunta real (valor puntual,
  #     tendencia, comparación, tabla o gráfica…);
  #   - sin frases «no usar para…»: la búsqueda no entiende la negación;
  #   - ≥ 40 caracteres cada una.
  - >
    [Responde/Calcula … a partir de la base de datos … . Se activa con
    preguntas sobre … .]
  - "[Tipo de pregunta 1: p. ej. cuánto … hay en un área marina protegida en un año.]"
  - "[Tipo de pregunta 2: p. ej. cómo ha cambiado … en el tiempo y si está aumentando.]"

# ── Parámetros (se convierten en el JSON Schema que lee el orquestador) ─────
# Por parámetro: type (string | integer | number | boolean | array), required,
# description y, si aplican, default, enum, minimum, maximum, items (tipo de los
# elementos de un array). Toda restricción numérica o de valores va como campo
# (minimum, maximum, enum), no sólo en la prosa: así el API la hace cumplir.
# `mutually_exclusive_with` es documental: el servicio no lo aplica, así que
# skill.R debe hacer stop() si llegan los dos.
# La `description` de cada input va en español y dice: qué columna de la base
# filtra (entre backticks), un ejemplo de valor, qué formato NO acepta y qué
# pasa si se omite.
inputs:
  fishing_office:
    type: string
    required: true
    description: >
      [Oficina de desembarque (`nombre_oficina`), p. ej. "CABO SAN LUCAS". Es la
      unidad de análisis. Siempre acompañada de `state`: los nombres de oficina
      se repiten entre estados.]
  state:
    type: string
    required: true
    description: >
      [Estado de la oficina (`nombre_estado`), p. ej. "BAJA CALIFORNIA SUR".]
  species:
    type: string
    required: false
    mutually_exclusive_with: resource_group
    description: >
      [Nombre científico canónico (`nombre_cientifico_canonico`), p. ej.
      "Lutjanus peru". No acepta nombres comunes. Si se omite junto con
      `resource_group`, se usan todas las especies.]
  resource_group:
    type: string
    required: false
    mutually_exclusive_with: species
    description: >
      [Grupo o recurso pesquero (`nombre_principal`), p. ej. "PARGO".]
  fleet:
    type: string
    required: false
    enum: [MAYORES, MENORES, COSECHA]
    description: >
      [Tipo de flota (`tipo_aviso`). Si se omite, se agregan todas.]
  year_from:
    type: integer
    required: false
    description: >
      [Primer año (inclusive). Si se omite, desde el primer año disponible.]
  year_to:
    type: integer
    required: false
    description: >
      [Último año (inclusive). Debe ser un año completo: si se omite, el último
      año completo de la entrega vigente.]
  n_boot:                        # ejemplo de parámetro de cómputo (no filtra datos)
    type: integer
    required: false
    default: 100
    minimum: 100
    maximum: 500
    description: >
      [Remuestreos bootstrap para el IC 95 %. La semilla es fija (ver Random
      controls).]

# ── Adquisición de datos ────────────────────────────────────────────────────
# Los datos de las bases del proyecto entran SIEMPRE por MCP: source: payload
# + provider. La skill nunca lee archivos ni abre conexiones.
# Una entrada por tabla que recibe run_skill(); `as` es el nombre del argumento.
# Arriba de cada entrada, un comentario dice qué filtros se empujan al MCP y
# cuáles NO (p. ej. un parámetro de cómputo como `n_boot` o `window` no va en
# params: lo usa skill.R).
acquire:
  # [Por qué esta tool y este group_by; tope de filas si la tool lo tiene.]
  - source: payload              # payload = el orquestador trae la tabla por MCP
    as: data                     # argumento de run_skill() que recibe la tabla
    provider:
      server: conapesca          # servidor MCP (conapesca | ltem | erddap)
      tool: get_landings         # tool que devuelve el contrato mínimo
      args:                      # argumentos fijos, iguales en toda llamada
        group_by: year_fleet
      params:                    # input de la skill → parámetro de la tool
        # Mapeo de transición a get_landings (los nombres de la tool no cambian
        # hasta que se migre): state → estado, fishing_office → oficina,
        # fleet → tipo_aviso, resource_group → nombre_principal,
        # species → nombre_cientifico_canonico. Verificar contra la firma real
        # de la tool en la rama desplegada del repo *-db-mcp.
        fishing_office: oficina
        state:          estado
        species:        nombre_cientifico_canonico
        resource_group: nombre_principal
        fleet:          tipo_aviso
        year_from:      year_from
        year_to:        year_to
    columns:                     # contrato mínimo: se valida ANTES de correr la
      - anio_corte               # skill (el error dice «falta la columna X»).
      - tipo_aviso               # Columnas con el nombre de la base, intactas.
      - total_kg
  # Fuente secundaria opcional: su ausencia no tumba la skill (required: false).
  # Borrar si la skill sólo tiene una tabla.
  - source: payload
    as: data_secondary
    required: false
    provider:
      server: ltem
      tool: family_biomass
      params:
        mpa:    mpa
        region: region
        reef:   reef
        year:   year
    columns:
      - year
      - family
      - mean_biomass
      - n_transects
  # Interdatabase: la tabla es la salida de otra skill (también va en depends_on).
  # - source: skill_output
  #   skill: ltem-nrsi-index
  #   as: data_nrsi
  #   columns: [time, reef, nrsi]

# ── Salida ──────────────────────────────────────────────────────────────────
output:
  table: main_table              # cuál elemento de run_skill()$value es LA tabla
                                 # del sobre. Omitir si value es un solo data.frame.
  columns: [anio_corte, total_tonnes]   # columnas de esa tabla (documental)
  scalars:                       # resultados de primer nivel de run_skill() además
                                 # de value/method/params (documental: viajan en
                                 # el sobre como `scalars`). Tipo + valores posibles.
    indicator: numeric           # [qué es, unidad, redondeo]
    category:  character         # ["valor_a" | "valor_b" | "valor_c"]

# ── Validación ──────────────────────────────────────────────────────────────
# Qué compara el arnés entre N corridas y contra la referencia. Puede nombrar
# columnas de output.table o escalares. Con bootstrap, incluir los límites del
# IC: la media es determinista aunque la semilla tenga fuga. Comparar también
# la dispersión, no sólo la media. Un comentario justifica la elección.
comparable_value: [indicator]
reference: references/cabo_pulmo_reference.json   # caso verificado por un humano
validation:
  params:                        # con qué corre el ARNÉS contra el fixture. No son
                                 # defaults del API. Obligatorio para todo input
                                 # required: true. Sólo nombres que estén en inputs.
    fishing_office: CABO SAN LUCAS
    state: BAJA CALIFORNIA SUR
depends_on: []                   # per-database: []. Interdatabase: [skill-a, skill-b]
---

# [Nombre legible de la skill]

## Purpose
[Una o dos frases: qué pregunta científica responde y qué devuelve (valor,
categoría, serie, tabla).]

[Alcance y escala: unidad de análisis (AMP, región, arrecife, oficina de
desembarque) y qué cambia con o sin cada filtro. Si se usa un proxy (p. ej. la
oficina de desembarque en lugar del AMP), decirlo aquí.]

## Data contract (minimal interface, NOT the local file)
Input `data` — [tool MCP y modo, p. ej. `get_landings(group_by = "year_fleet")`]:

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `[columna]` | [integer/numeric/character/logical] | [unidad o —] | [qué es] |

[Repetir una tabla por cada entrada de `acquire` (indicar si es opcional).]

- **Already applied by the MCP:** [filtros, agregación (p. ej. suma por transecto →
  media por arrecife), unidad en que llega (p. ej. t/ha; la skill no convierte).]
- **Not applied (by the MCP or by this skill):** [filtros o limpiezas que otro
  análisis sí aplica (p. ej. `ltem_report`), y por qué los valores no son
  directamente comparables.]
- **Missing-data rule:** [qué pasa con NA y ceros: excluir / imputar / marcar.
  Nunca un NaN silencioso.]
- **Aggregation unit:** [transecto / arrecife-año / viaje / año. Fija, no opcional.]
- **Incomplete periods:** [cómo se trata un año parcial de la entrega vigente.]
- **Row cap:** [tope de filas de la tool y qué hace la skill si se alcanza; o
  «Not applicable».]
- **Data source:** [base y entrega; curación declarada aquí (p. ej. pipeline
  `conapesca-database`), no en References.]

## Method (fixed, no degrees of freedom)
[Una frase con el método y su referencia bibliográfica.]

```
1. DATA ALREADY FILTERED BY MCP ([filtros])

2. [PASO]
   [fórmula o regla exacta]

3. [PASO]
   [redondeo: n decimales]

4. [CATEGORIZE, si aplica]
   [umbral → categoría]
```

- Parameters (documented defaults): [parámetro = valor, rango].
- Implementation: [paquete y función de R, p. ej. `mgcv::gam(method = "REML")`].
- [Umbrales o categorías: fuente bibliográfica, o «convención interna sin fuente».]

### Interpretation
[Borrar si la skill no interpreta.] Computed on [serie anual sobre la que se
interpreta]:
- Before/after comparison (`before_after()`): first 5 years vs. last 5 years.
- Mann-Kendall test (Mann, 1945; Kendall, 1975) via `mk_trend()`
  (`shared/interpretation/interpret.R`); minimum number of years as set in `mk_trend()`.
- Status: [regla exacta para "positive" / "negative" / "neutral" / "ambiguous"].

## Random controls
<!-- El arnés lee esta sección por texto (incluidos los comentarios) y extrae la
semilla de «Seed: <número>». Si la skill es determinista, borrar esta sección
entera y escribir sólo la frase estándar que usa conapesca-tmca en su sección
Random controls (no se copia aquí a propósito: si esa frase aparece en la
sección, el arnés trata la skill como determinista aunque tenga semilla). -->
- Seed: [42]. [Dónde se fija (`set.seed(42L)` una vez antes del bucle) y de qué
  depende el resultado (orden de los grupos, datos completos).]
- [Bootstrap: qué se remuestrea, con reemplazo, `n_boot` por defecto.]

## Output structure
```r
list(
  value     = <data.frame>,  # [main_table: columnas]
  [scalar]  = <numeric>,     # [qué es, unidad, redondeo]
  method    = <character>,
  params    = list([parámetros efectivos usados])
)
```

- [Descripción de las columnas de salida que no son obvias.]
- Plot: [opcional; el sobre del servicio de skills no lleva gráficos.]

Example chatbot output:
*"[Frase de ejemplo con el valor, la unidad, el periodo y la categoría.]"*

## Reference value and tolerance
- Reference cases: [n] (`[métricas]`) in `references/cabo_pulmo_reference.json`.
- Case: [sitio, filtros, periodo, fila comparada].
- Expected values: PENDING: needs a value verified by a human. Do NOT use the
  skill's own output as reference.
  <!-- Al verificar: «[valor] [unidad], verified by [persona] ([AAAA-MM-DD]) with an
  independent calculation on [fuente] (snapshot [AAAA-MM-DD])». -->
- Tolerance: [±x] ([razón: la skill redondea a n decimales]).
- Seed: [42 / not applicable].
- Status: PENDING.

## Do-not rules
- Do NOT [error conocido 1] — [por qué y qué hacer en su lugar].
- Do NOT [error conocido 2].

## Validation checklist
- [ ] self-consistency: run N times on fixed data, outputs match within tolerance.
- [ ] reference: output matches the `references/` value within tolerance.
- [ ] coherence: the output uses the methods this contract specifies.
- [ ] [Verificación específica de la skill.]

## Success criteria
A complete analysis with this skill includes:
- [Elemento 1.]
- [Elemento 2.]

## References
<!-- APA 7. Citas fijas de las bases (sin fecha de consulta ni cobertura: esas
van en data_snapshot del caso de referencia):
- Comisión Nacional de Acuacultura y Pesca. (2026). *Avisos de arribo y de cosecha*
  [Datos sin publicar, obtenidos mediante solicitud de acceso a la información pública
  núm. 340008100012626, Plataforma Nacional de Transparencia; entregados el 29 de junio
  de 2026].
- Centro para la Biodiversidad Marina y la Conservación. (2026). *Programa de
  Monitoreo Ecológico de Largo Plazo (LTEM)* [Datos sin publicar].
Si la skill usa Mann-Kendall: Mann (1945), Kendall (1975) y el paquete Kendall
(McLeod). Paquetes de R con su versión. -->
- [Base de datos.]
- [Método.]

## Planned changes
<!-- Opcional. Borrar si no aplica. -->
> PENDING: [cambio planeado]. No modifica el contrato actual.
- Requires: [dependencia].
