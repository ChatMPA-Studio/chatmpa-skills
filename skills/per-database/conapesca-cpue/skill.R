# skill.R — conapesca-cpue
#
# Computes CPUE (kg / effective fishing day) as mean-of-ratios per folio,
# disaggregated by fleet type (MAYORES / MENORES).
#
# Two modes:
#   Panel mode   (office_filter specified): one office, generates plot.
#   Utility mode (office_filter = NULL):    all offices, no plot.
#                Used internally by conapesca-landings-timeseries and
#                conapesca-national-ranking (when CPUE ranking is implemented).
#
# See SKILL.md for the full data contract, method, and do-not rules.

if (!exists("before_after", mode = "function")) {
  source(file.path(dirname(sys.frame(1)$ofile),
                   "../../shared/interpretation/interpret.R"))
}

# ── Constants (fixed — do not change without updating SKILL.md) ──────────────

.MIN_TRIPS_WARN <- 5L
.VALID_AVISOS   <- c("MAYORES", "MENORES")  # COSECHA always excluded

# Tableau 10 palette — consistent across all conapesca skills
.FLEET_COLORS <- c(MAYORES = "#4E79A7", MENORES = "#F28E2B")
.FLEET_SHAPES <- c(MAYORES = 17L, MENORES = 16L)  # filled triangle, filled circle

# ── run_skill ─────────────────────────────────────────────────────────────────
#
# Args:
#   data                       data.frame — from get_landings(group_by="folio").
#                              Required cols: folio_aviso, anio_corte, tipo_aviso,
#                              nombre_estado, nombre_oficina,
#                              peso_desembarcado_kg,
#                              dias_efectivos, dias_efectivos_fuente,
#                              flag_fecha_generica, flag_dias_efectivos_sospechoso,
#                              flag_periodo_futuro
#   office_filter              character or NULL.
#                              Panel mode  (specified): filter to one office; plot generated.
#                              Utility mode (NULL):     all offices; no plot; output
#                              includes nombre_oficina and nombre_estado columns.
#   state_filter               character or NULL. Recommended when office_filter is
#                              specified (office names not unique across states).
#                              When office_filter = NULL, use to restrict universe
#                              (e.g. by litoral/region when implemented).
#   resource_group             character or NULL — resource group filter (nombre_principal). NULL = all.
#   species                    character or NULL — species filter (nombre_cientifico_canonico). NULL = all.
#                              Mutually exclusive with resource_group.
#   year_range                 integer vector c(start, end) or NULL — NULL = all years.
#
# Returns (panel mode):   list(value, plot, method, params)
# Returns (utility mode): list(value, plot = NULL, method, params)
#   value columns (utility mode) add: nombre_oficina, nombre_estado

run_skill <- function(data,
                      office_filter  = NULL,
                      state_filter   = NULL,
                      resource_group = NULL,
                      species        = NULL,
                      year_range     = NULL,
                      ...) {

  # ── Input validation ───────────────────────────────────────────────────────

  # nombre_principal / nombre_cientifico_canonico absent: get_landings(group_by="folio")
  # aggregates at folio level and does not return species columns. Species/resource
  # filtering is applied server-side by the MCP via the params block in SKILL.md.
  required_cols <- c("folio_aviso", "anio_corte", "tipo_aviso",
                     "nombre_estado", "nombre_oficina",
                     "peso_desembarcado_kg", "dias_efectivos",
                     "dias_efectivos_fuente", "flag_fecha_generica",
                     "flag_dias_efectivos_sospechoso", "flag_periodo_futuro")
  missing_cols <- setdiff(required_cols, names(data))
  if (length(missing_cols) > 0)
    stop("Missing columns in data: ", paste(missing_cols, collapse = ", "))

  panel_mode <- !is.null(office_filter) && nzchar(office_filter)

  if (panel_mode && (is.null(state_filter) || !nzchar(state_filter)))
    warning("'state_filter' is recommended with 'office_filter' — ",
            "office names are not unique across states.")
  if (!is.null(resource_group) && !is.null(species))
    stop("'resource_group' and 'species' are mutually exclusive.")
  if (!is.null(year_range) &&
      (length(year_range) != 2 || !is.numeric(year_range) || year_range[1] > year_range[2]))
    stop("'year_range' must be a two-element numeric vector c(start, end).")

  # ── Step 1: Filter ─────────────────────────────────────────────────────────

  base_mask <- data$tipo_aviso %in% .VALID_AVISOS & data$peso_desembarcado_kg > 0

  if (panel_mode)
    base_mask <- base_mask & (data$nombre_oficina == office_filter)
  if (!is.null(state_filter) && nzchar(state_filter))
    base_mask <- base_mask & (data$nombre_estado == state_filter)
  # Species/resource_group filters are applied server-side by the MCP; no
  # client-side column check needed here.
  if (!is.null(year_range))
    base_mask <- base_mask &
                 data$anio_corte >= year_range[1] &
                 data$anio_corte <= year_range[2]

  folios_base    <- data[base_mask, ]
  n_folios_total <- nrow(folios_base)

  if (n_folios_total == 0)
    stop("No records found.",
         if (panel_mode)                            paste0(" office='", office_filter, "'"),
         if (!is.null(state_filter))                paste0(" state='", state_filter, "'"),
         if (!is.null(resource_group))  paste0(" resource_group='", resource_group, "'"),
         if (!is.null(species))         paste0(" species='", species, "'"))

  # Quality filters (applied after counting total for n_viajes_excluidos)
  data_clean <- folios_base[
    !folios_base$flag_fecha_generica            &
    !folios_base$flag_dias_efectivos_sospechoso &
    !is.na(folios_base$dias_efectivos), ]

  n_excluidos <- n_folios_total - nrow(data_clean)

  if (nrow(data_clean) == 0)
    stop("No valid records after quality filters.")

  # ── Step 2: CPUE per folio ─────────────────────────────────────────────────
  # dias_efectivos is already folio-level — do NOT sum across rows

  data_clean$cpue_folio <- data_clean$peso_desembarcado_kg / data_clean$dias_efectivos

  # ── Step 3: Aggregate ─────────────────────────────────────────────────────
  # Panel mode:   group by anio_corte × tipo_aviso
  # Utility mode: group by nombre_oficina × nombre_estado × anio_corte × tipo_aviso

  group_cols <- if (panel_mode) {
    c("anio_corte", "tipo_aviso")
  } else {
    c("nombre_oficina", "nombre_estado", "anio_corte", "tipo_aviso")
  }

  combos <- unique(data_clean[, group_cols, drop = FALSE])
  combos <- combos[do.call(order, combos), ]

  value <- do.call(rbind, lapply(seq_len(nrow(combos)), function(i) {
    mask <- rep(TRUE, nrow(data_clean))
    for (col in group_cols)
      mask <- mask & (data_clean[[col]] == combos[[col]][i])

    sub      <- data_clean[mask, ]
    n_viajes <- nrow(sub)
    n_recomp <- sum(sub$dias_efectivos_fuente == "recomputado", na.rm = TRUE)

    if (n_viajes < .MIN_TRIPS_WARN)
      warning(paste(combos[i, ], collapse = " | "),
              ": n_viajes=", n_viajes, " < ", .MIN_TRIPS_WARN,
              " — CPUE mean unreliable.")

    mask_base <- rep(TRUE, nrow(folios_base))
    for (col in group_cols)
      mask_base <- mask_base & (folios_base[[col]] == combos[[col]][i])
    n_excluidos_combo <- nrow(folios_base[mask_base, ]) - nrow(sub)

    row <- as.data.frame(combos[i, , drop = FALSE], stringsAsFactors = FALSE)
    row$cpue_media                 <- round(mean(sub$cpue_folio), 4)
    row$cpue_sd                    <- round(sd(sub$cpue_folio), 4)
    row$n_viajes                   <- n_viajes
    row$n_viajes_excluidos         <- n_excluidos_combo
    row$peso_desembarcado_kg_total <- sum(sub$peso_desembarcado_kg)
    row$n_viajes_recomputado       <- n_recomp
    row
  }))

  rownames(value) <- NULL

  # ── Interpretation ────────────────────────────────────────────────────────
  # Per-fleet (MENORES / MAYORES) on regional scale. Status = ambiguous:
  # declining CPUE may reflect overfishing, stock depletion, or reduced effort.

  .cpue_interp <- function(fleet_label, fleet_label_es, aviso) {
    fleet_df <- value[value$tipo_aviso == aviso, ]
    fleet_df <- fleet_df[order(fleet_df$anio_corte), ]
    # Rename so before_after uses standard "year" column
    fleet_df$year <- fleet_df$anio_corte
    if (nrow(fleet_df) < 2) return(list(status = "insufficient_data"))

    all_yrs <- sort(unique(fleet_df$year))
    ba  <- before_after(fleet_df, "cpue_media",
                        before_years = head(all_yrs, 5L), recent_n = 5L)
    mkt <- mk_trend(fleet_df, "cpue_media")

    sentences <- if (!is.null(ba$status)) {
      list(en = NA_character_, es = NA_character_)
    } else {
      caution_en <- "Note: CPUE trends reflect both effort and stock — interpret with caution."
      caution_es <- "Nota: La CPUE refleja esfuerzo y abundancia — interprete con precaución."
      insight_sentence(
        var_label_en  = fleet_label,
        var_label_es  = fleet_label_es,
        unit          = "kg/day",
        before_mean   = ba$before_mean, after_mean = ba$after_mean,
        delta         = ba$delta,       pct_change = ba$pct_change,
        before_period = ba$before_period, after_period = ba$after_period,
        extra_en      = caution_en,     extra_es   = caution_es,
        digits        = 1L
      )
    }

    list(
      before_period = ba$before_period,
      after_period  = ba$after_period,
      metric_before = ba$before_mean,
      metric_after  = ba$after_mean,
      delta         = ba$delta,
      pct_change    = ba$pct_change,
      direction     = if (!is.null(ba$direction)) ba$direction else "unknown",
      status        = "ambiguous",
      significance  = mkt,
      insight_es    = sentences$es,
      insight_en    = sentences$en
    )
  }

  interpretation <- list(
    menores = .cpue_interp("Artisanal (MENORES) CPUE",
                           "La CPUE artesanal (MENORES)", "MENORES"),
    mayores = .cpue_interp("Industrial (MAYORES) CPUE",
                           "La CPUE industrial (MAYORES)", "MAYORES")
  )

  # ── Step 4: Plot (panel mode only) ────────────────────────────────────────

  plot <- if (panel_mode) {
    .build_cpue_plot(value, office_filter, resource_group, species)
  } else {
    NULL
  }

  # ── Return ─────────────────────────────────────────────────────────────────

  list(
    value          = value,
    interpretation = interpretation,
    plot           = plot,
    method = paste0(
      "Mean-of-ratios CPUE: mean(sum_kg_folio / dias_efectivos_folio) ",
      "per ", paste(group_cols, collapse = " x "), ". ",
      "Quality filters: flag_fecha_generica=FALSE, ",
      "flag_dias_efectivos_sospechoso=FALSE, !is.na(dias_efectivos). ",
      "COSECHA excluded. MAYORES and MENORES always separate."
    ),
    params = list(
      mode                       = if (panel_mode) "panel" else "utility",
      office_filter              = office_filter,
      state_filter               = state_filter,
      resource_group = resource_group,
      species        = species,
      year_range                 = year_range,
      flotas                     = .VALID_AVISOS,
      min_trips_warn             = .MIN_TRIPS_WARN
    )
  )
}

# ── .build_cpue_plot ──────────────────────────────────────────────────────────
# Internal. Panel mode only. See SKILL.md for visual spec.

.build_cpue_plot <- function(value, office_filter, resource_group, species) {

  if (!requireNamespace("ggplot2", quietly = TRUE))
    stop("Package 'ggplot2' is required to generate the CPUE plot.")
  if (!requireNamespace("scales", quietly = TRUE))
    stop("Package 'scales' is required to generate the CPUE plot.")

  value$reliable <- value$n_viajes >= .MIN_TRIPS_WARN

  dummy <- value[1L, ]
  dummy$anio_corte <- NA_integer_
  dummy$cpue_media <- NA_real_
  dummy$tipo_aviso <- "n < 5 viajes"
  dummy$reliable   <- FALSE

  filled_layer_data <- rbind(value[value$reliable, ], dummy)

  fleet_levels <- c("MAYORES", "MENORES", "n < 5 viajes")
  value$tipo_aviso             <- factor(value$tipo_aviso, levels = fleet_levels)
  filled_layer_data$tipo_aviso <- factor(filled_layer_data$tipo_aviso, levels = fleet_levels)

  real_data  <- value
  unreliable <- value[!value$reliable, ]

  cpue_range <- range(value$cpue_media, na.rm = TRUE)
  use_log    <- (cpue_range[2L] / cpue_range[1L]) > 10

  y_scale <- if (use_log) {
    ggplot2::scale_y_log10(
      labels = scales::label_number(accuracy = 0.1, big.mark = ","),
      name   = "CPUE (kg / dia efectivo)"
    )
  } else {
    ggplot2::scale_y_continuous(
      labels = scales::label_number(accuracy = 0.1, big.mark = ","),
      name   = "CPUE (kg / dia efectivo)"
    )
  }

  filter_label <- if (!is.null(resource_group)) {
    paste0("Recurso: ", resource_group)
  } else if (!is.null(species)) {
    paste0("Especie: ", species)
  } else {
    "Todos los recursos"
  }

  ggplot2::ggplot(mapping = ggplot2::aes(x = anio_corte, y = cpue_media,
                                          color = tipo_aviso, shape = tipo_aviso)) +
    ggplot2::geom_line(data = real_data, linewidth = 0.8, na.rm = TRUE) +
    ggplot2::geom_point(data = filled_layer_data, size = 4, stroke = 1.2, na.rm = TRUE) +
    ggplot2::geom_point(data = unreliable, shape = 1L, size = 4, stroke = 1.5,
                        show.legend = FALSE) +
    y_scale +
    ggplot2::scale_x_continuous(breaks = scales::breaks_pretty(n = 8)) +
    ggplot2::scale_color_manual(
      name   = NULL,
      values = c(.FLEET_COLORS, "n < 5 viajes" = "grey60"),
      labels = c(MAYORES = "Flota mayor", MENORES = "Flota menor",
                 "n < 5 viajes" = "n < 5 viajes")
    ) +
    ggplot2::scale_shape_manual(
      name   = NULL,
      values = c(.FLEET_SHAPES, "n < 5 viajes" = 1L),
      labels = c(MAYORES = "Flota mayor", MENORES = "Flota menor",
                 "n < 5 viajes" = "n < 5 viajes")
    ) +
    ggplot2::labs(subtitle = filter_label, x = "A\u00f1o") +
    ggplot2::theme_minimal(base_size = 12) +
    ggplot2::theme(
      legend.position  = "bottom",
      legend.direction = "horizontal",
      panel.grid.minor = ggplot2::element_blank(),
      plot.subtitle    = ggplot2::element_text(color = "grey40")
    )
}
