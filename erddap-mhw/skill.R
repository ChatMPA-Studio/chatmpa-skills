# skill.R — erddap-mhw
#
# Detects Marine Heatwave (MHW) events at a marine protected area from daily
# OISST SST data, reporting annual heatwave days, event counts, and mean peak
# intensity using the heatwaveR protocol (Hobday et al. 2016).
#
# See SKILL.md for the full data contract and method specification.
#
# Dependencies:
#   shared/spatial_join/spatial_join.R  — clip_to_geometry(), get_amp_geometry()
#   heatwaveR                           — ts2clm(), detect_event()

source(file.path(dirname(sys.frame(1)$ofile),
                 "../../shared/spatial_join/spatial_join.R"))

if (!exists("before_after", mode = "function")) {
  source(file.path(dirname(sys.frame(1)$ofile),
                   "../../shared/interpretation/interpret.R"))
}

# ── Constants (fixed — do not change without updating SKILL.md) ──────────────

.CLIM_PERIOD     <- c("1982-01-01", "2011-12-31")  # Hobday et al. 2016 baseline
.PCTILE          <- 90L                             # MHW threshold: 90th percentile
.MIN_DURATION    <- 5L                              # min consecutive days above threshold
.JOIN_GAPS       <- TRUE                            # merge events separated by ≤ 2 days
.MIN_BASELINE_YRS <- 20L                            # minimum years for reliable climatology
.MIN_PIXELS_WARN  <- 4L                             # warn if fewer pixels than this

# ── run_skill ────────────────────────────────────────────────────────────────
#
# Args:
#   data           data.frame — daily OISST from ERDDAP MCP:
#                  columns: lat (num), lon (num), time (Date or character), sst (num)
#   geometry_local sf object  — AMP polygon, from get_amp_geometry()
#
# Returns: list(value, interpretation, method, params, geometry_source)
#   value columns: year (int), kpi_mhw_days_per_yr (int), n_events_per_yr (int),
#                  mean_intensity_per_yr (num, °C above threshold)

run_skill <- function(data, ...) {

  if (!requireNamespace("heatwaveR", quietly = TRUE)) {
    stop("Package 'heatwaveR' required. Install with: install.packages('heatwaveR')")
  }

  # ── Resolve geometry for metadata (geometry_source only, no spatial clip) ──
  args <- list(...)
  mpa  <- args$mpa
  geometry_local <- if (!is.null(mpa) && nzchar(mpa)) {
    tryCatch(get_amp_geometry(mpa), error = function(e) NULL)
  } else NULL

  # ── Input validation ───────────────────────────────────────────────────────

  # data is pre-aggregated from MCP (aggregate_spatial=TRUE):
  # columns: time (chr/Date), sst (num) — one row per day, spatial mean over bbox
  required_cols <- c("time", "sst")
  missing_cols  <- setdiff(required_cols, names(data))
  if (length(missing_cols) > 0) {
    stop("Missing columns in data: ", paste(missing_cols, collapse = ", "),
         "\nExpected: ", paste(required_cols, collapse = ", "),
         " (aggregate_spatial=TRUE response from ERDDAP MCP)")
  }

  # ── Step 1: Build daily time series ──────────────────────────────────────
  # data is already a spatial mean — no clip_to_geometry needed.

  ts_daily <- data.frame(t = as.Date(data$time), temp = data$sst)
  ts_daily <- ts_daily[!is.na(ts_daily$temp), ]
  ts_daily <- ts_daily[order(ts_daily$t), ]

  # Verify baseline coverage
  baseline_start <- as.Date(.CLIM_PERIOD[1])
  baseline_end   <- as.Date(.CLIM_PERIOD[2])
  n_baseline_yrs <- length(unique(format(
    ts_daily$t[ts_daily$t >= baseline_start & ts_daily$t <= baseline_end], "%Y"
  )))

  if (n_baseline_yrs < .MIN_BASELINE_YRS) {
    stop("Baseline period (", .CLIM_PERIOD[1], " to ", .CLIM_PERIOD[2], ") has only ",
         n_baseline_yrs, " years of data — climatology unreliable. Need >= ",
         .MIN_BASELINE_YRS, " years.")
  }

  # ── Step 2: Climatology (ts2clm) ─────────────────────────────────────────

  clim <- heatwaveR::ts2clm(
    ts_daily,
    climatologyPeriod = .CLIM_PERIOD,
    pctile            = .PCTILE
  )

  # ── Step 3: Event detection (detect_event) ────────────────────────────────

  mhw       <- heatwaveR::detect_event(clim,
                                        minDuration    = .MIN_DURATION,
                                        joinAcrossGaps = .JOIN_GAPS)
  clim_out  <- mhw$climatology  # one row per day: t, temp, seas, thresh, event, ...
  event_out <- mhw$event        # one row per event: date_start, duration, intensity_max, ...

  # ── Step 4: Annual aggregation ────────────────────────────────────────────

  clim_out$year <- as.integer(format(clim_out$t, "%Y"))
  all_years     <- sort(unique(clim_out$year))

  # MHW days per year (days flagged as event == TRUE in climatology output)
  mhw_days <- aggregate(event ~ year, data = clim_out,
                         FUN = function(x) sum(as.logical(x), na.rm = TRUE))
  names(mhw_days)[names(mhw_days) == "event"] <- "kpi_mhw_days_per_yr"

  # Events per year and mean peak intensity (based on event start year)
  if (!is.null(event_out) && nrow(event_out) > 0) {
    event_out$year <- as.integer(format(as.Date(event_out$date_start), "%Y"))

    n_events <- aggregate(duration ~ year, data = event_out, FUN = length)
    names(n_events)[names(n_events) == "duration"] <- "n_events_per_yr"

    mean_int <- aggregate(intensity_max ~ year, data = event_out,
                           FUN = function(x) round(mean(x, na.rm = TRUE), 3))
    names(mean_int)[names(mean_int) == "intensity_max"] <- "mean_intensity_per_yr"

    events_annual <- merge(n_events, mean_int, by = "year", all = TRUE)
  } else {
    events_annual <- data.frame(
      year                  = all_years,
      n_events_per_yr       = 0L,
      mean_intensity_per_yr = NA_real_
    )
  }

  # Merge all annual metrics; years with no events get 0
  value <- merge(data.frame(year = all_years), mhw_days,     by = "year", all.x = TRUE)
  value <- merge(value,                         events_annual, by = "year", all.x = TRUE)
  value$kpi_mhw_days_per_yr[is.na(value$kpi_mhw_days_per_yr)] <- 0L
  value$n_events_per_yr[is.na(value$n_events_per_yr)]         <- 0L
  rownames(value) <- NULL

  # ── Interpretation ────────────────────────────────────────────────────────
  # Compare 1982-2000 baseline against last 5 years for MHW days per year.

  ba_mhw  <- before_after(value, "kpi_mhw_days_per_yr", year_col = "year",
                           before_years = 1982:2000, recent_n = 5L)
  mkt_mhw <- mk_trend(value, "kpi_mhw_days_per_yr", year_col = "year")

  mhw_status <- if (!is.null(ba_mhw$status)) "neutral" else {
    if (ba_mhw$delta > 10 ||
        (ba_mhw$direction == "increasing" &&
         !is.null(mkt_mhw$p) && mkt_mhw$p < 0.10)) "negative"
    else if (ba_mhw$delta <= 0 && ba_mhw$after_mean < 5) "positive"
    else "neutral"
  }

  mhw_sentences <- if (!is.null(ba_mhw$status)) {
    list(en = NA_character_, es = NA_character_)
  } else {
    insight_sentence(
      var_label_en  = "Marine Heatwave days per year",
      var_label_es  = "Días de ola de calor marina por año",
      unit          = "days/yr",
      before_mean   = ba_mhw$before_mean, after_mean = ba_mhw$after_mean,
      delta         = ba_mhw$delta,       pct_change = ba_mhw$pct_change,
      before_period = ba_mhw$before_period, after_period = ba_mhw$after_period,
      digits        = 1L
    )
  }

  interpretation <- list(
    before_period = ba_mhw$before_period,
    after_period  = ba_mhw$after_period,
    metric_before = ba_mhw$before_mean,
    metric_after  = ba_mhw$after_mean,
    delta         = ba_mhw$delta,
    pct_change    = ba_mhw$pct_change,
    direction     = if (!is.null(ba_mhw$direction)) ba_mhw$direction else "unknown",
    status        = mhw_status,
    significance  = mkt_mhw,
    insight_es    = mhw_sentences$es,
    insight_en    = mhw_sentences$en
  )

  # ── Return ────────────────────────────────────────────────────────────────

  list(
    value  = value,
    interpretation = interpretation,
    method = paste0(
      "Marine Heatwave detection via heatwaveR (Hobday et al. 2016). ",
      "Step 1: daily SST time series from ERDDAP MCP (aggregate_spatial=TRUE, bbox mean). ",
      "Step 2: ts2clm climatology, baseline ", .CLIM_PERIOD[1],
      " to ", .CLIM_PERIOD[2], ", threshold = ", .PCTILE, "th percentile. ",
      "Step 3: detect_event with minDuration = ", .MIN_DURATION,
      ", joinAcrossGaps = ", .JOIN_GAPS, ". ",
      "Step 4: annual aggregation of MHW days, events, and mean peak intensity. ",
      "Dataset: ncdcOisst21Agg_LonPM180, NOAA CoastWatch ERDDAP."
    ),
    params = list(
      climatology_period = .CLIM_PERIOD,
      pctile             = .PCTILE,
      min_duration       = .MIN_DURATION,
      join_across_gaps   = .JOIN_GAPS,
      min_pixels_warn    = .MIN_PIXELS_WARN
    ),
    geometry_source = list(
      local = if (!is.null(geometry_local)) attr(geometry_local, "geometry_source") else "bbox_aggregate"
    )
  )
}
