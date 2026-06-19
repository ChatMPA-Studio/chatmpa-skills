# Statistical Approaches for MPA Analysis

Reference for analyzing MPA effectiveness with the LTEM dataset. The central
concern is the **hierarchical, nested sampling design**: transects are nested
within depth strata, within reef-years, within reefs, within regions. Treating
non-independent observations as independent (pseudoreplication) inflates the
effective sample size and produces falsely significant results. Every method
below is framed around respecting that structure.

## The Pseudoreplication Problem

```
Region → Reef → Year → Depth → Transect → Species → Size class
```

The **transect is the independent replicate** (one belt transect = one diver
swim = 250 m²). Multiple transects share a reef-year-depth; multiple reefs
share a region. These shared levels create correlation among observations.

| Wrong | Why it fails | Right |
|-------|--------------|-------|
| Treat each species×size row as an `n` | Thousands of correlated rows | Sum to transect totals first |
| Pool all transects as independent | Ignores reef/year clustering | Model clustering or aggregate |
| Compare reef means with unequal effort | Unbalanced, biased | Use transect unit or weight |

**Rule:** sum biomass/abundance within a transect, then treat transects as the
replicate. For tests reported as `n`, use the number of unique transects.

---

## Choosing a Design

| Design | Data required | What it estimates | Use when |
|--------|---------------|-------------------|----------|
| Control-Impact (CI) | Protected + reference sites, one or many years | Current inside-vs-outside gap | No pre-protection data |
| Before-After (BA) | One site across protection onset | Change over time at the site | No good controls |
| BACI | Controls + impact, before + after | Protection effect net of background | Both available (preferred) |

LTEM begins in 1998 (Cabo Pulmo protected 1995), so a strict "before" is
unavailable; early years serve as an approximate baseline, and CI / BACI-style
contrasts against contemporaneous reference sites carry most of the inference.

---

## Effect Sizes

Always report an effect size alongside any p-value — significance alone says
nothing about magnitude.

- **Log response ratio (lnRR):** `ln(X_protected / X_reference)`. Primary metric;
  back-transform to a fold-change with `exp()`. See `mpa_effectiveness_metrics.md`.
- **Median percent difference:** robust for skewed biomass data:
  `(median_protected − median_reference) / median_reference × 100`.
- **Standardized mean difference (Cliff's delta / rank-biserial):** non-parametric
  effect size paired with Mann-Whitney U.
- **BACI interaction:** `(Impact_after − Impact_before) − (Control_after − Control_before)`,
  in original biomass units.

---

## Parametric Tests and Assumptions

Reef-fish biomass is typically **right-skewed and heteroscedastic** (many small
values, occasional large schools). Before using t-tests or ANOVA:

1. Check normality of residuals (Shapiro-Wilk, Q-Q plot).
2. Check homogeneity of variance (Levene's test).
3. If violated, transform (`log(x)` or `log(x+1)` for biomass/abundance) or use
   a non-parametric alternative.

Log-transformation often normalizes biomass and converts multiplicative
protection effects into additive ones, which suits linear models.

---

## Non-Parametric Options

Robust defaults when assumptions fail and clustering is handled by aggregation.

| Test | Use | LTEM application |
|------|-----|------------------|
| Mann-Whitney U | Two-group comparison | Protected vs reference transect biomass |
| Kruskal-Wallis | ≥3 groups | Across protection levels |
| Dunn's test | Post-hoc after Kruskal-Wallis | Pairwise, with p-adjustment |
| Spearman ρ | Monotonic trend | Biomass vs year, or vs distance from MPA |

```python
from scipy import stats
# Transect-level biomass, n = number of transects
stat, p = stats.mannwhitneyu(protected, reference, alternative='greater')
```

These tests assume independent observations — valid only after aggregating to
the transect level. They do not, by themselves, account for reef/year
clustering; for that, use mixed models.

---

## Mixed-Effects Models (Recommended)

Linear mixed-effects models (LMMs) and their generalized form (GLMMs) handle the
nested structure directly by including **random effects** for grouping levels,
rather than collapsing them away. This is the most rigorous approach for LTEM.

Conceptual structure for an inside-vs-outside biomass comparison:

```
log(biomass + 1) ~ protection_level            # fixed effect of interest
                   + (1 | region/reef)          # nested random intercepts
                   + (1 | year)                 # temporal random effect
```

- **Fixed effects:** the contrasts you want to estimate (protection level,
  period, their interaction for BACI; depth, trophic group as covariates).
- **Random effects:** reef nested in region, plus year, absorb the
  non-independence so the fixed-effect standard errors are not understated.
- **Family:** Gaussian on log-transformed biomass, or a Tweedie / Gamma / negative
  binomial GLMM for raw biomass or counts with many zeros.

BACI in a mixed model is the `period × treatment` interaction term:

```
response ~ period * treatment + (1 | reef) + (1 | year)
```

A significant, positive interaction is the protection effect net of background
change. Fit with `statsmodels` (`mixedlm`) in Python or `lme4`/`glmmTMB` in R;
report fixed-effect estimates, their CIs, and the variance attributed to each
random level.

---

## Multiple Comparisons

Comparing several protection levels, metrics, trophic groups, or years inflates
the family-wise error rate. Control it:

| Method | Controls | When |
|--------|----------|------|
| Bonferroni | Family-wise error (conservative) | Few comparisons |
| Holm | Family-wise error (more power) | General-purpose default |
| Benjamini-Hochberg (FDR) | False discovery rate | Many metrics/species screened |

```python
from statsmodels.stats.multitest import multipletests
reject, p_adj, _, _ = multipletests(pvals, method='holm')
```

Report adjusted p-values and state the correction used. For exploratory
species-by-species screens, FDR is usually the appropriate trade-off.

---

## Temporal Autocorrelation

Repeated annual surveys at a reef are correlated through time. When modeling
trajectories:

- Include `year` as a random effect (above), or
- Fit a trend (e.g., GLS / mixed model with an AR(1) correlation structure on
  year within reef), and
- Avoid treating consecutive years at one reef as independent replicates.

For simple trend detection, the Mann-Kendall test (monotonic trend) and Sen's
slope (trend magnitude) are robust, non-parametric options.

---

## Reporting Standards

- [ ] State the replicate explicitly (transect) and report `n` as transect count.
- [ ] Describe aggregation: sum within transect, then analyze.
- [ ] Name the design (CI / BA / BACI) and the model structure.
- [ ] Report effect size **and** uncertainty (CI), not just p-values.
- [ ] State assumption checks and any transformation applied.
- [ ] State the multiple-comparison correction when >1 test is run.
- [ ] Account for reef/region/year clustering via mixed models or aggregation.
