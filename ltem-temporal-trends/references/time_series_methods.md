# Statistical Methods for Ecological Time Series

Reference for analyzing temporal trends in LTEM fish metrics (biomass, abundance, richness, size). These methods are read on-demand when deeper detail than the SKILL.md workflow is needed.

## Overview

Ecological time series are typically **short, noisy, irregularly sampled, and autocorrelated**. The 26-year LTEM record (1998-2024) yields at most ~27 annual data points per metric. Choose methods that are robust to small `n`, non-normal residuals, and missing years.

| Question | Recommended method |
|----------|--------------------|
| Is there a monotonic trend? | Mann-Kendall test |
| How fast is it changing? | Sen's slope |
| Is the trend linear? | Linear regression (parametric) |
| Is there a nonlinear trend? | GAM / LOESS / STL |
| Is there serial dependence? | ACF / PACF, Durbin-Watson |
| Is there a seasonal cycle? | STL / classical decomposition |

## Trend Tests

### Mann-Kendall test

A **non-parametric** test for a monotonic (not necessarily linear) trend. It makes no distributional assumption and is robust to outliers, making it a standard choice in ecology and hydrology.

The statistic `S` counts the sign of all pairwise differences:

```
S = Σ_{i<j} sign(x_j - x_i)
```

For `n` ≤ ~10 use exact tables; for larger `n` use the normal approximation with variance

```
Var(S) = n(n-1)(2n+5) / 18     (subtract a tie-correction term when ties exist)
z = (S - sign(S)) / sqrt(Var(S))
```

- **H0:** no monotonic trend. Reject when `|z|` exceeds the critical value (e.g. 1.96 at α = 0.05).
- **Assumption:** observations are independent. Positive autocorrelation inflates the false-positive rate — use a **modified Mann-Kendall** (e.g. Hamed-Rao or Yue-Wang variance correction) when the residuals are autocorrelated.
- **Seasonal Mann-Kendall** handles within-year cycles by computing `S` within each season and summing; not needed if LTEM data are pre-aggregated to annual values.

### Sen's slope (Theil-Sen estimator)

The companion magnitude estimate to Mann-Kendall: the **median of all pairwise slopes**.

```
slope = median{ (x_j - x_i) / (t_j - t_i) : i < j }
```

Robust to up to ~29% outliers and far less sensitive than ordinary least squares. Report it alongside an OLS slope; large divergence between the two flags influential points or nonlinearity. A confidence interval follows from the rank of the sorted pairwise slopes.

```python
import pymannkendall as mk
result = mk.original_test(annual_ts['biomass_per_reef'])
# result.trend, result.p, result.slope (Sen's slope), result.intercept
```

## Autocorrelation

Adjacent years are rarely independent: a high-biomass year tends to be followed by another. This **temporal autocorrelation** violates the independence assumption of OLS and most trend tests, deflating standard errors and exaggerating significance.

- **ACF** (autocorrelation function): correlation of the series with itself at lag *k*. A slow decay indicates trend or strong persistence.
- **PACF** (partial ACF): correlation at lag *k* after removing shorter lags; identifies AR order.
- **Durbin-Watson** statistic (~2 = no autocorrelation, <2 = positive) tests regression residuals.

Mitigation:
1. Use modified Mann-Kendall (variance correction).
2. Model the autocorrelation explicitly — e.g. GLS with an AR(1) error structure, or a GAM with correlated errors.
3. Block-bootstrap or permutation tests that preserve serial structure.

## Decomposition

Separate an observed series into interpretable components:

```
Additive:        Y_t = Trend_t + Seasonal_t + Residual_t
Multiplicative:  Y_t = Trend_t × Seasonal_t × Residual_t
```

Use multiplicative (or log-transform then additive) when the seasonal amplitude grows with the level — common for biomass/abundance.

**STL (Seasonal-Trend decomposition using Loess)** is the preferred general-purpose method: it is robust to outliers, allows the seasonal component to evolve, and handles any seasonal period.

```python
from statsmodels.tsa.seasonal import STL
res = STL(monthly_series, period=12, robust=True).fit()
trend, seasonal, resid = res.trend, res.seasonal, res.resid
```

For LTEM, surveys are usually pooled to **annual** values, so the seasonal term is often dropped; decomposition then reduces to trend + residual (effectively a smoother). Apply STL only when sub-annual (monthly) structure is retained.

## Smoothing

Smoothers reveal the trend by suppressing year-to-year noise. They are descriptive, not inferential — do not read significance from a smoothed line.

| Smoother | Notes |
|----------|-------|
| Moving average | Simple; `center=True` avoids phase lag. Loses ends. |
| LOESS / LOWESS | Local regression; flexible, good for irregular spacing. |
| Savitzky-Golay | Polynomial fit in a sliding window; preserves peaks. Needs `window_length` odd and ≥ `polyorder + 2`. |
| Kernel / spline | Continuous, tunable bandwidth. |

Window/bandwidth controls the bias-variance trade-off: wide = smooth but over-flattened; narrow = follows noise. With only ~27 points keep windows modest (e.g. 5 years).

```python
from scipy.signal import savgol_filter
smoothed = savgol_filter(y, window_length=7, polyorder=2)
```

## Generalized Additive Models (GAMs)

GAMs extend regression by replacing linear terms with smooth functions `f(·)` fitted by penalized splines:

```
g(E[Y_t]) = β0 + f(year) + f(SST) + ...
```

Strengths for ecological series:
- Capture **nonlinear** trends without specifying the form a priori.
- Use an appropriate **error family** (Gaussian for log-biomass, Poisson/negative-binomial for counts, Tweedie for biomass with many zeros).
- The **effective degrees of freedom** (edf) of the year smooth indicate trend complexity (edf ≈ 1 → essentially linear).
- Autocorrelation can be incorporated (e.g. `gamm` with an AR(1) term).

Penalization (smoothing parameter, chosen by GCV or REML) guards against overfitting — important given small `n`. In Python use `pygam`; in R, `mgcv::gam`.

```python
from pygam import LinearGAM, s
gam = LinearGAM(s(0)).fit(years.reshape(-1, 1), y)
gam.summary()   # check edf and significance of the smooth
```

## Handling Short and Irregular Ecological Series

LTEM data are not a clean evenly-spaced series. Practical guidance:

- **Power is limited.** With <10–15 points, only strong trends are detectable. Report effect sizes (Sen's slope, total change) and confidence intervals, not just p-values. A non-significant result is not evidence of no change.
- **Missing years.** Prefer methods that tolerate gaps (Mann-Kendall, Sen's slope, GAMs) over those requiring regular spacing. Interpolate sparingly and never fabricate trend through gaps; flag interpolated points.
- **Unequal effort.** Standardize metrics per unit effort (per transect / per reef / per area) before building the series, per the SKILL.md aggregation rules.
- **Uncertainty per year.** Each annual value is a mean over transects with its own SE. Carry that uncertainty into plots (error bars / ribbons) and, where possible, into weighted or hierarchical models.
- **Define `n` correctly.** For trend inference, `n` is the number of **years**, not transects or rows.
- **Transformations.** Log or square-root transforms stabilize variance for biomass/abundance and linearize multiplicative growth; back-transform for reporting.
- **Multiple metrics / regions.** Testing many series inflates family-wise error — apply a correction (e.g. Benjamini-Hochberg FDR) when scanning all regions or species.

## Reporting Checklist

- [ ] Per-effort standardized series with annual uncertainty
- [ ] Trend direction and significance (Mann-Kendall, autocorrelation-checked)
- [ ] Magnitude (Sen's slope + total change over the period)
- [ ] Linear vs nonlinear assessment (OLS vs GAM/LOESS)
- [ ] Autocorrelation diagnostics reported
- [ ] Missing-data handling stated explicitly

## See Also

- `change_point_detection.md` — abrupt shifts and breakpoints
- `regime_shifts.md` — ecological regime-shift interpretation
