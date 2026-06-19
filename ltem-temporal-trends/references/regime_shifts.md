# Marine Ecosystem Regime Shifts

A **regime shift** is a large, abrupt, and persistent reorganization of an ecosystem's structure and function — a move from one quasi-stable state ("regime") to another. Unlike a smooth trend, a regime shift involves a relatively rapid transition and, often, **hysteresis**: reversing the driver does not immediately reverse the state. For LTEM reef-fish systems, regime-shift framing helps interpret whether observed change is steady, reversible drift or a more fundamental restructuring.

## Concept

Ecosystems can possess **multiple stable states** maintained by feedbacks. A gradually changing external driver (warming SST, sustained fishing) may have little visible effect until a **threshold (tipping point)** is crossed, after which the system flips to an alternative state.

```
        state
          |        ____ regime B
          |       /
          |      |   <- abrupt transition near threshold
          | ____/
          |/  regime A
          +------------------------> driver (e.g. SST, fishing pressure)
```

Key properties:
- **Nonlinearity** — small driver change near the threshold produces a large state change.
- **Persistence** — the new regime is self-reinforcing and outlasts brief perturbations.
- **Hysteresis** — recovery requires pushing the driver well past the original threshold (the return path differs from the forward path).

Not every shift is a true alternative-state regime shift; some are smooth, reversible responses that merely look abrupt when sampled annually. Distinguishing the two is central to interpretation.

## Drivers in Reef-Fish Systems

| Driver | Typical effect |
|--------|----------------|
| Marine heatwaves / warming SST | Thermal stress, **tropicalization** (warm-affinity species replace temperate ones), range shifts |
| ENSO (El Niño / La Niña) | Large interannual productivity and recruitment swings; can trigger or mask shifts |
| Overfishing | Removal of top predators / large-bodied species; **trophic restructuring** |
| Protection (MPA establishment) | Recovery shift: predator and biomass rebound (e.g. recovery trajectories in protected reefs) |
| Habitat change | Loss of structural complexity alters fish assemblage |

Drivers frequently interact — fishing can erode resilience so that a climate event tips a system that would otherwise have absorbed it.

## Early-Warning Signals (EWS)

As a system approaches a tipping point, its dynamics slow ("**critical slowing down**"): it recovers more sluggishly from perturbations. This leaves statistical fingerprints in the time series *before* the shift.

| Indicator | Expected change near a tipping point |
|-----------|--------------------------------------|
| **Variance** (or SD) | Rises — fluctuations grow as resilience weakens |
| **Lag-1 autocorrelation** | Rises toward 1 — successive years become more similar |
| **Skewness** | May increase as the system leans toward the alternate state |
| **Return rate** | Falls — slower recovery from perturbations |

```python
# Rolling early-warning indicators on a detrended series
detrended = y - savgol_filter(y, 7, 2)
roll_var = pd.Series(detrended).rolling(window=7).var()
roll_ar1 = pd.Series(detrended).rolling(window=7).apply(
    lambda w: pd.Series(w).autocorr(lag=1), raw=False)
# Test for a trend (e.g. Kendall's tau) in roll_var and roll_ar1
```

**Caveats.** EWS are suggestive, not definitive. They require **detrending** first (so the rising variance reflects dynamics, not the trend itself), are sensitive to window choice, and are statistically weak on short series — the ~27-year LTEM record gives only a handful of independent rolling windows. Treat rising variance + rising autocorrelation together as a flag for closer inspection, not as proof.

## Gradual Trend vs Abrupt Shift

The core interpretive question: is the change **continuous** (a trend) or a **state transition** (a shift)?

| Feature | Gradual trend | Abrupt regime shift |
|---------|---------------|---------------------|
| Rate | Steady, proportional to driver | Slow, then sudden near threshold |
| Reversibility | Reverses when driver reverses | Hysteresis; hard to reverse |
| Time-series signature | Monotonic (Mann-Kendall, Sen's slope) | Step / breakpoint (Pettitt, PELT) + EWS |
| Best fitting model | Linear / smooth GAM | Two-regime / segmented model |

**How to distinguish in practice:**
1. Fit both a smooth-trend model (linear or GAM) and a change-point / two-regime model; compare via information criteria (AIC/BIC) or out-of-sample fit.
2. Run a change-point test (`change_point_detection.md`). A single, sharp, multi-metric break supports a shift; a weak break with strong monotonic Mann-Kendall supports a trend.
3. Inspect EWS before any candidate break — critical slowing down supports a genuine tipping point.
4. Check **concordance** across biomass, abundance, richness, size structure, and trophic composition. A coordinated jump across many metrics is the strongest evidence for a regime shift; change in one metric alone usually is not.

## Ecological Interpretation in Reef-Fish Systems

When a candidate shift is detected, interpret structure, not just totals:

- **Trophic restructuring.** A drop in top-predator and large-bodied biomass with a rise in lower-trophic or small-bodied species signals fishing-driven or release-driven reorganization. Track mean trophic level and predator:prey biomass ratios across the break.
- **Tropicalization.** A turnover from temperate to tropical / warm-affinity species, coincident with warming SST or a marine heatwave, indicates a climate-driven assemblage shift rather than a simple abundance change.
- **Recovery shifts (MPAs).** Inside well-enforced protection, an upward step in predator biomass and large-fish abundance can mark a recovery regime — the desirable direction of a shift. Contrast protected vs unprotected trajectories around the same years.
- **Size-structure change.** Truncation of the size spectrum (loss of large individuals) often precedes biomass collapse and is an ecologically meaningful early signal.

Always cross-reference the timing of a detected shift with:
- **Environmental records** — SST anomalies, marine heatwave years, ENSO phase, chlorophyll.
- **Management events** — MPA designation, gear or catch regulation changes.
- **Other LTEM metrics** — to confirm system-wide rather than single-metric change.

## Reporting Guidance

- State explicitly whether the evidence supports a **trend** or a **regime shift**, and on what basis (model comparison, change-point test, EWS, concordance).
- Pair every claimed shift with its candidate driver(s) and acknowledge alternatives.
- Quantify the transition: before/after means, percent change, and which assemblage components moved.
- Be candid about uncertainty — short series, autocorrelation, and limited EWS power all weaken regime-shift inference. Avoid asserting causation from correlation alone.

## See Also

- `time_series_methods.md` — trend tests, autocorrelation, GAMs
- `change_point_detection.md` — detecting the break that may mark a shift
