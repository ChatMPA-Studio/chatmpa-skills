# Standard MPA Evaluation Metrics

Reference for the core response variables used to assess Marine Protected Area
(MPA) effectiveness with the LTEM dataset. Each metric below states what it
measures, how it is computed from transect-level data, and how to interpret it
in a conservation context. All computations assume data have first been
aggregated correctly (sum within transect, then average across transects) to
avoid pseudoreplication — see `statistical_methods.md`.

## Summary Table

| Metric | What it captures | Direction expected in effective MPA |
|--------|------------------|-------------------------------------|
| Biomass density | Standing stock per unit area | Higher inside |
| Density (abundance) | Individuals per unit area | Higher (often) inside |
| Response ratio (lnRR) | Standardized inside-vs-outside effect | Positive |
| Predator / target biomass | Recovery of exploited groups | Strongly higher inside |
| Trophic structure | Food-web completeness | Larger top-predator share inside |
| Size spectrum | Body-size distribution | Shallower slope, more large fish inside |
| Recovery trajectory | Change through time | Increasing toward asymptote |
| BACI contrast | Protection effect net of background | Positive interaction |

---

## 1. Biomass and Density

### Biomass density
Standing-stock biomass standardized to area. From transect totals:

```
biomass_density = (Σ biomass over species in transect) / transect_area
```

LTEM transects are 250 m² (50 m × 5 m); densities are commonly expressed per
100 m² or scaled to ton/ha. Biomass is the single most responsive and widely
reported MPA indicator because protection releases fish from fishing mortality,
allowing individuals to survive and grow.

### Abundance density
Numerical density of individuals per unit area, computed the same way from
`quantity`. Abundance responds less consistently than biomass: protection often
increases mean body size more than counts, so biomass can rise even when density
is flat.

---

## 2. Response Ratio (lnRR)

The log response ratio is the standard effect-size metric for inside-vs-outside
and before-vs-after MPA contrasts. It is symmetric, variance-stabilizing, and
comparable across sites and studies.

```
lnRR = ln( X_protected / X_reference )
```

where `X` is a mean response (e.g., biomass density) for each group.

| lnRR | Interpretation |
|------|----------------|
| 0 | No difference |
| 0.69 | Protected ≈ 2× reference |
| 1.10 | Protected ≈ 3× reference |
| < 0 | Protected lower than reference |

Back-transform with `exp(lnRR)` to report a fold-change. Compute on
transect-level means; propagate uncertainty from the variance of both groups.
Response ratios can also be tracked annually to show how the effect builds over
time.

```python
import numpy as np
ln_rr = np.log(protected_mean / reference_mean)
fold_change = np.exp(ln_rr)   # e.g., 4.3x
```

---

## 3. Predator and Target-Species Biomass

Top predators and commercially targeted species are removed first and recover
last under protection, so their biomass is the most diagnostic MPA signal.

- **Predator biomass:** sum biomass of high-trophic-level taxa (commonly
  `trophic_level ≥ 4.0`) per transect, then average by protection level.
- **Target-species biomass:** restrict to a defined list of fished taxa
  (e.g., groupers, snappers, jacks) and compute biomass density the same way.

Interpretation: a large inside-vs-outside gap in predator/target biomass —
larger than the gap for the whole assemblage — indicates protection is
relieving fishing pressure rather than reflecting habitat differences. A flat
predator response despite "protected" status suggests weak enforcement.

---

## 4. Trophic Structure

Trophic structure describes how biomass is partitioned across the food web.
Effective no-take protection restores top-down structure, shifting biomass
toward higher trophic levels.

Group taxa by trophic level, sum biomass per group, and express as a proportion
of total assemblage biomass within each protection level:

| Group | Trophic level | 
|-------|---------------|
| Herbivores | < 2.5 |
| Omnivores | 2.5 – 3.5 |
| Carnivores | 3.5 – 4.0 |
| Top predators | ≥ 4.0 |

Key indicators:
- **Top-predator biomass share** — fraction of total biomass in the top group.
- **Mean community trophic level** — biomass-weighted mean of `trophic_level`.

A higher top-predator share and higher mean trophic level inside the MPA signal
ecosystem-level recovery, not just more fish of the same kind. A declining mean
trophic level over time outside the MPA can indicate "fishing down the food web."

---

## 5. Size Spectra

Body size integrates growth, survival, and fishing history. Protection allows
fish to reach larger sizes, which matters disproportionately because fecundity
scales steeply (often more than linearly) with body mass.

### Size-class distribution
Bin individuals by total length and compare the proportional distribution
between protection levels. The fraction of large fish (e.g., > 40 cm) is a
simple, robust MPA indicator.

### Size spectrum slope
Plot log abundance against log body-size class; fit a linear regression. The
slope summarizes how abundance declines with size.

```
log10(N) = a + b · log10(size_class)
```

A **shallower (less negative) slope** indicates relatively more large
individuals — the expected MPA signature. Steep slopes characterize heavily
fished assemblages dominated by small fish. Always weight or normalize for the
binning scheme and report the size range fitted.

---

## 6. Recovery Trajectories

For a no-take reserve with a time series, the recovery trajectory is the change
in a response variable (usually biomass) from a baseline through time.

```
recovery_factor(t) = X(t) / X(baseline)
```

LTEM surveys begin in 1998, three years after Cabo Pulmo's 1995 establishment,
so the earliest years approximate (but post-date) baseline conditions.

Interpretation:
- Recovery is typically **non-linear**, rising steeply then approaching an
  asymptote (carrying capacity). A logistic or saturating curve often fits.
- A `recovery_factor` substantially greater than 1 that plateaus indicates a
  recovered, stable assemblage.
- Compare the protected trajectory against reference sites over the same years
  to separate protection effects from region-wide drivers (warming, ENSO,
  productivity).

---

## 7. Inside-vs-Outside and Before-vs-After Contrasts

These are the two spatial/temporal comparison frameworks underlying most
metrics above.

### Inside vs outside (control-impact)
Compare protected sites against ecologically comparable reference (fished)
sites surveyed in the same years. Strength: directly measures the current
protection gap. Weakness: confounded if sites differed before protection
(habitat, depth, exposure) — match reference sites carefully.

### Before vs after
Compare a site against itself across the protection onset. Strength: controls
for fixed site characteristics. Weakness: confounded by region-wide temporal
trends unless paired with controls.

### Combined (BACI)
The before-after-control-impact design isolates the protection effect as the
**interaction** — the change inside net of the change outside:

```
BACI effect = (Impact_after − Impact_before) − (Control_after − Control_before)
```

A positive interaction attributable to protection (rather than to background
change shared with controls) is the strongest single line of evidence for MPA
effectiveness. See `statistical_methods.md` for the corresponding models and
significance testing.

---

## Reporting Checklist

- [ ] State the spatial/temporal framework (inside-outside, before-after, BACI).
- [ ] Report metrics on transect-level data with `n` = number of transects.
- [ ] Pair each effect size (lnRR or fold-change) with a dispersion measure.
- [ ] Include at least one structural metric (trophic or size), not biomass alone.
- [ ] Distinguish target/predator responses from whole-assemblage responses.
- [ ] For reserves, show the trajectory through time, not just a single contrast.
