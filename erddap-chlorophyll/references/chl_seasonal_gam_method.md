# Chlorophyll-a Seasonal Climatology — Method Reference

## Seasonal climatology: cyclic GAM on log10(Chl-a)

### Rationale

Chl-a is log-normally distributed (see `../SKILL.md` §Method). A simple
arithmetic monthly mean over the baseline period violates this: bloom months
contribute disproportionately and the resulting climatology overestimates the
typical seasonal level. All climatology estimation must be done in log10 space,
consistent with the annual geometric mean computation in `skill.R`.

Additionally, months are a **cyclic** variable — December must connect
continuously to January. Fixed monthly means treat each month independently
and produce a discontinuous boundary. A cyclic spline enforces periodicity.

### Model

Fit on all baseline monthly observations (one row per pixel-month or
spatially-averaged month, depending on input resolution):

```r
gam_clim <- mgcv::gam(
  log10(chla) ~ s(month, bs = "cc", k = 6),
  data   = baseline_data,   # filtered to baseline period
  method = "REML"
)
```

- **`bs = "cc"`** — cyclic cubic regression spline. Boundary knots at 0.5 and
  12.5 (i.e., the spline wraps: the value and first derivative at month 1 equal
  those at month 12). This is the correct basis for any periodic variable with a
  known period (here, 12 months).
- **`k = 6`** — 5 effective degrees of freedom (edf); sufficient to capture a
  unimodal or bimodal seasonal cycle without overfitting to monthly-resolution
  data. With only 12 distinct x-values per year, k > 6 risks overfitting the
  baseline variability rather than the true seasonal signal.
- **`method = "REML"`** — restricted maximum likelihood for smoothing parameter
  estimation; standard recommendation for GAMs (Wood 2011).

Predictions are made for months 1–12 on the log10 scale and back-transformed:

```r
pred      <- predict(gam_clim, newdata = data.frame(month = 1:12), se.fit = TRUE)
clim_chla <- 10^pred$fit          # geometric mean climatology (mg/m³)
clim_lo   <- 10^(pred$fit - 1.96 * pred$se.fit)  # 95% CI lower
clim_hi   <- 10^(pred$fit + 1.96 * pred$se.fit)  # 95% CI upper
```

### Anomaly

For each observed month in a target year:

```
anomaly_log10 = log10(observed_chla) - log10(climatology_chla)
              = log10(observed_chla / climatology_chla)
```

Interpretation: `anomaly_log10 > 0` → above climatology; `< 0` → below. A value
of +0.3 means ~2× the climatological level (one doubling in base-10 units);
−0.3 means ~0.5× (one halving). This matches the `HIGH_PROD_THRESHOLD` and
`LOW_PROD_THRESHOLD` constants in `skill.R`.

### Long-term trend

Annual geometric means are tested for monotonic trend with **Mann-Kendall**
(non-parametric; robust to non-normality and serial correlation):

```r
Kendall::MannKendall(annual_geomean_chla)
```

Slope magnitude can be estimated with **Sen's slope** (`trend::sens.slope()`).
Mann-Kendall is preferred over OLS because Chl-a annual series are typically
short (< 25 years), skewed, and may contain autocorrelation.

### Baseline period

**2004–2013** (10 years). This matches the available MODIS data coverage from
the NPP coastal zone dataset (`NPP_coastal_zone_2004-2023.RDS`). The first
decade is used as baseline to allow the second decade (2014–2023) to reveal
trend departures without including recent anomalous years in the reference.

In production (ERDDAP 8-day composites), the baseline extends to 2003–2020
per `skill.R`. The 2004–2013 window is specific to the local proxy dataset
used in `test_outputs/run_tests.R`.

## References

- Wood, S.N. (2017). *Generalized Additive Models: An Introduction with R*
  (2nd ed.). Chapman & Hall/CRC. — GAM framework, cyclic spline basis (`bs="cc"`),
  REML smoothing parameter estimation.
- Wood, S.N. (2011). Fast stable restricted maximum likelihood and marginal
  likelihood estimation of semiparametric generalized linear models. *Journal
  of the Royal Statistical Society (B)*, 73(1), 3–36.
- Kendall, M.G. (1975). *Rank Correlation Methods*. Griffin, London. — Mann-Kendall
  statistic for monotonic trend detection.
- Mann, H.B. (1945). Nonparametric tests against trend. *Econometrica*, 13, 245–259.
- Campbell, J.W. (1995). The lognormal distribution as a model for bio-optical
  variability in the sea. *Journal of Geophysical Research: Oceans*, 100(C7),
  13237–13254. — Establishes log-normal as the appropriate model for Chl-a.
