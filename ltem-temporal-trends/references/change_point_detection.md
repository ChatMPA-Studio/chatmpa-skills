# Change Point Detection Algorithms

A **change point** is a moment in a time series where the statistical properties — most often the mean, but sometimes the variance or trend — shift abruptly. In LTEM fish series, change points may mark ecological responses to El Niño / La Niña, marine heatwaves, fishing-pressure changes, or the onset of MPA recovery.

This reference complements the Pettitt and CUSUM code already in SKILL.md, adding the assumptions and the multi-change-point algorithms.

## What Counts as a Change Point

| Type of change | Detected by |
|----------------|-------------|
| Shift in mean (level) | Pettitt, CUSUM, PELT, binary segmentation |
| Shift in variance | CUSUM-of-squares, variance-cost segmentation |
| Change in trend (slope) | Segmented / breakpoint regression |
| Change in distribution | Non-parametric / kernel change point methods |

Be explicit about *which* property you expect to change before choosing a method.

## Single Change Point Methods

### Pettitt's test

A **non-parametric** rank-based test for a single shift in the median, derived from the Mann-Whitney statistic. Widely used in hydrology and ecology because it needs no distributional assumption and is robust to outliers.

```
U_{t,n} = Σ_{i=1}^{t} Σ_{j=t+1}^{n} sign(x_i - x_j)
K = max_t |U_{t,n}|        # change point = the t that maximizes it
p ≈ 2 exp( -6 K² / (n³ + n²) )
```

- **H0:** no change point (homogeneous series).
- **Assumptions:** at most one change point; observations independent. It loses power if the true change is near the series ends.
- **Output:** the location `t` and an approximate p-value. Report the before/after means.

### CUSUM (cumulative sum)

Tracks the running sum of deviations from the overall mean:

```
S_t = Σ_{i=1}^{t} (x_i - x̄)
```

A change in mean appears as a **change in the slope** of `S_t` (an upward-then-downward bend, or a clear vee). The change point is `argmax |S_t|`; significance is judged by a **bootstrap** (permute the series, recompute the CUSUM range, compare). CUSUM is excellent for visualization but, used alone, only identifies one dominant shift.

## Multiple Change Point Methods

Real ecological series may contain several shifts. These methods solve for the set of change points that best partitions the series, balancing **goodness of fit** against a **penalty** for adding break points.

```
minimize  Σ_k Cost(segment_k)  +  penalty × (number of change points)
```

`Cost` is typically the negative log-likelihood (Gaussian mean/variance change) or a sum-of-squares.

### Binary segmentation

Greedy and fast (`O(n log n)`): find the single best change point in the whole series, split, then recurse on each half until no further split improves the criterion. Approximate — it can miss change points and is biased when shifts are close together. Good first pass.

### PELT (Pruned Exact Linear Time)

An **exact** dynamic-programming method that, with a linear penalty, runs in roughly linear time thanks to pruning. Given a sensible penalty it returns the globally optimal change-point set, making it the preferred general-purpose multiple-change-point algorithm.

```python
import ruptures as rpt
algo = rpt.Pelt(model="rbf").fit(signal)          # "l2" mean, "rbf" distribution
change_points = algo.predict(pen=penalty)         # indices of segment ends
# Or fix the number of breaks instead of a penalty:
# rpt.Dynp(model="l2").fit(signal).predict(n_bkps=2)
```

### Window-based and kernel methods

Slide a window and compare the two halves with a discrepancy measure (mean, kernel/RBF). Useful for non-parametric distributional changes; sensitive to window width.

## Choosing the Penalty

The penalty is the single most consequential choice — too small over-segments (spurious breaks), too large misses real ones.

| Penalty | Idea |
|---------|------|
| **AIC** | `2 × n_params`; tends to keep more change points. |
| **BIC / SIC** | `log(n) × n_params`; more conservative — common default. |
| **MBIC** | Modified BIC penalizing segment-length imbalance. |
| Manual | Tune by inspecting an **elbow plot** of cost vs number of change points. |

Practical advice for short LTEM series:
- Start with BIC, then sweep the penalty and watch how the change-point set stabilizes (an "elbow" / penalty-vs-segments curve).
- Impose a **minimum segment length** (e.g. ≥ 3–5 years) so single anomalous years are not flagged as regimes.
- Cross-check across metrics: a real ecosystem shift usually appears in several variables at the same time.

## Segmented / Breakpoint Regression

When the change is in the **slope** rather than the level, fit piecewise-linear regression with one or more breakpoints:

```
y = β0 + β1·t            for t ≤ τ
y = β0 + β1·t + β2·(t-τ)  for t > τ      # τ = breakpoint, estimated
```

`β2` measures the change in slope; its significance tests whether the trend genuinely changed. The breakpoint `τ` is estimated iteratively (e.g. R `segmented`, or Python `piecewise-regression`). Compare against a single-line model with an F-test or information criterion to justify the extra break. Davies' test assesses whether a breakpoint exists at all.

## Assumptions and Pitfalls

- **Independence.** Most tests assume independent observations; autocorrelation inflates false change points. Check the ACF first (see `time_series_methods.md`).
- **Edge effects.** Change points near the start or end are poorly estimated and statistically weak — interpret cautiously.
- **Short series.** With ~27 annual points, prefer detecting **one or two** robust changes over many; demand a minimum segment length.
- **Outliers vs shifts.** A single extreme year (e.g. an El Niño spike) is an outlier, not a regime change. Non-parametric methods (Pettitt) and robust costs reduce this confusion.
- **Significance vs description.** PELT/binary segmentation return locations but not p-values; pair them with a test (Pettitt, bootstrap CUSUM) or out-of-sample validation before claiming a "significant" shift.
- **Multiple testing.** Scanning many metrics/regions for change points inflates false positives; correct or require concordance.

## Interpreting a Detected Change Point

A change point is a statistical signal, not an explanation. To make it ecologically meaningful:

1. **Locate it in time** and list candidate drivers active in that window (ENSO phase, marine heatwave, MPA designation date, fishing regulation).
2. **Quantify the shift** — before/after means, percent change, slope change.
3. **Check concordance** — does the same year appear in biomass, abundance, richness, and size? Multi-metric agreement strengthens the case for a true regime change.
4. **Test against environmental covariates** (SST, chlorophyll) to separate climate-driven from anthropogenic shifts.
5. **Distinguish gradual from abrupt** — see `regime_shifts.md`. A gradual trend can produce an apparent single change point; segmented regression vs Pettitt helps adjudicate.

## See Also

- `time_series_methods.md` — trend tests, autocorrelation, decomposition
- `regime_shifts.md` — ecological regime shifts and early-warning signals
