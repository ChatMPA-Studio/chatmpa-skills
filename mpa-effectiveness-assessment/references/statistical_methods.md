# Statistical Testing Approaches for MPA Assessment

Guidance on choosing and applying statistical tests when comparing
biodiversity, biomass, or community metrics between protected and reference
areas. The right design depends on what data are available (snapshot vs
time series, single vs multiple sites) and on whether assumptions hold.

## Study Designs

### Control-Impact (CI)

Compare the **impact** (inside MPA) with one or more **control** (reference)
locations sampled at the same time. This is the most common design when only
a post-protection snapshot exists. Its weakness: a difference could pre-date
protection or reflect habitat differences rather than the MPA itself.

### Before-After-Control-Impact (BACI)

The strongest commonly feasible design. Samples are collected at both control
and impact locations **before and after** protection. The effect of protection
is the *interaction* `Time(Before/After) × Location(Control/Impact)`: a true
MPA effect appears as a change inside that is not mirrored at controls.

| | Before | After |
|---|--------|-------|
| **Impact (inside)** | baseline | response |
| **Control (outside)** | baseline | reference change |

BACI requires baseline data, so it is only available where monitoring predates
designation. When multiple control sites and multiple times are available, the
design extends to **Beyond-BACI** (multiple controls) and BACIPS (paired series).

## Two-Group Tests (CI snapshot)

| Test | Use when | Notes |
|------|----------|-------|
| Student's t-test | Two groups, approximately normal residuals, similar variances | Welch's t-test relaxes equal-variance |
| Mann–Whitney U | Two groups, non-normal or ordinal data, small n | Tests stochastic dominance / shift; rank-based |
| Permutation test | Few assumptions; resample group labels | Good for skewed ecological data |

**t-test vs Mann–Whitney:** prefer the t-test when residuals are roughly
normal (often true after log-transforming biomass/abundance). Use Mann–Whitney
for skewed counts, heavy tails, small samples, or when you do not want to
assume a distribution. Mann–Whitney tests a shift in distribution, not means.

```python
import scipy.stats as stats
# Welch's t-test on log-biomass
stats.ttest_ind(np.log1p(inside), np.log1p(outside), equal_var=False)
# Non-parametric alternative
stats.mannwhitneyu(inside, outside, alternative='greater')
```

## Multiple Sites and Mixed Models

When data span many sites, transects nested in sites, or repeated years,
ordinary two-group tests are inappropriate because observations are not
independent. Use **linear mixed-effects models (LMMs)** or generalized
linear mixed models (GLMMs):

- **Fixed effect:** protection status (and covariates: depth, habitat, year).
- **Random effects:** site, and transect nested within site, to absorb spatial
  grouping; year as random when many years are sampled.

```python
import statsmodels.formula.api as smf
# Biomass ~ protection, with site as a random intercept
model = smf.mixedlm("log_biomass ~ protected + depth",
                    data=df, groups=df["site"])
result = model.fit()
print(result.summary())
```

For count or presence data use a GLMM with an appropriate family (Poisson or
negative binomial for counts; binomial for presence/absence). For
multivariate community composition, **PERMANOVA** (permutational MANOVA on a
distance matrix) tests differences in assemblage structure between protection
levels.

## Effect Sizes

Always report an effect size alongside any test. p-values reflect both effect
magnitude and sample size; effect sizes convey ecological relevance.

| Effect size | Pairs with | Range / meaning |
|-------------|-----------|-----------------|
| Log response ratio (lnRR) | biomass/density ratios | 0 = no effect (see `mpa_metrics.md`) |
| Cohen's d | t-test | standardized mean difference |
| Cliff's delta | Mann–Whitney | −1 to 1; probability of dominance |
| Hedges' g | small-sample d | bias-corrected Cohen's d |

Report confidence intervals on the effect size whenever possible.

## Assumptions to Check

| Assumption | How to check | If violated |
|-----------|--------------|-------------|
| Normality of residuals | Q–Q plot, Shapiro–Wilk | Transform (log/sqrt) or use non-parametric |
| Homogeneity of variance | Levene's test, residual plot | Welch's t-test; model variance structure |
| Independence | Study design | Mixed models; correct unit of replication |
| Linearity (models) | Residual-vs-fitted plot | Add terms / transform |

Count and biomass data are typically right-skewed; a `log` or `log1p`
transform often satisfies normality and equal-variance assumptions
simultaneously.

## Pseudoreplication

The most common error in MPA studies. **Pseudoreplication** occurs when the
unit of analysis is treated as independent when it is not — e.g. comparing
hundreds of transects from a *single* MPA against transects from a *single*
reference area and testing "protection" with transect-level n. The true
replicate for the protection effect is the **location/MPA**, not the transect.

Avoid it by:

- Defining the correct experimental unit (site or MPA, not transect).
- Using mixed models with site/MPA as a random effect so within-site
  replicates inform precision but do not inflate degrees of freedom.
- Replicating across **multiple** MPAs and **multiple** reference areas where
  possible; a single inside/single outside contrast cannot separate "MPA
  effect" from "this particular place" effect.

## Reporting Checklist

- [ ] State the design (CI, BACI, Beyond-BACI).
- [ ] Identify the unit of replication and confirm independence.
- [ ] Report test statistic, df, p-value, **and** effect size with CI.
- [ ] State transformations and assumption checks performed.
- [ ] Note sample sizes per group.
