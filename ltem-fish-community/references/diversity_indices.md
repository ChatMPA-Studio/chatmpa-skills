# Diversity Indices

Detailed explanation of the diversity metrics used in the LTEM fish community workflow. Each index summarizes a different facet of community structure — how many species are present, how individuals are distributed among them, and how those properties scale with sampling effort. These metrics are computed in the skill's `calculate_diversity_metrics()` step, after data have been aggregated to the survey level (see `ltem_methodology.md` and the Core Workflow in `SKILL.md`).

## Notation

All abundance-based indices operate on the proportional abundances of species in a sample.

| Symbol | Meaning |
|--------|---------|
| `S` | Number of species (richness) |
| `n_i` | Number of individuals of species *i* |
| `N` | Total individuals, `N = Σ n_i` |
| `p_i` | Proportional abundance of species *i*, `p_i = n_i / N` |

In the LTEM data, abundance is the `quantity` column summed within a transect (or survey) for each species, following the aggregation rules in `SKILL.md`. Use SUM-then-MEAN aggregation before computing indices so that the independent sampling unit (the transect) is respected.

## Species Richness (S)

The simplest diversity metric: a count of the distinct species present.

```
S = number of species with n_i > 0
```

```python
S = (group['quantity'] > 0).sum()         # within an aggregated group
# or, on raw long-format rows:
S = group.loc[group['quantity'] > 0, 'species'].nunique()
```

**Interpretation.** Richness ignores abundance — a sample with one rare and one dominant species has the same `S` as a perfectly even pair. It is strongly sensitive to sampling effort: more transects or larger area generally yield more species. For fair comparisons across sites or years, equalize effort (equal numbers of transects) or use rarefaction (below).

## Shannon Index (H')

The Shannon–Wiener index measures uncertainty in predicting the species of a randomly drawn individual. It increases with both richness and evenness.

```
H' = -Σ ( p_i * ln(p_i) )      summed over species with p_i > 0
```

```python
import numpy as np

def shannon(quantities):
    n = np.asarray(quantities, dtype=float)
    n = n[n > 0]
    if n.sum() == 0:
        return 0.0
    p = n / n.sum()
    return -np.sum(p * np.log(p))
```

**Interpretation.** `H'` ranges from 0 (one species) to `ln(S)` (all species equally abundant). Typical reef-fish values fall roughly in the 1.5–3.5 range when natural logs are used, but the absolute number depends on the log base, so always report the base. The skill uses natural logs (`np.log`), so `H'` is in *nats*. Shannon weights common and rare species relatively evenly and is the most widely reported diversity index in monitoring programs.

## Simpson Index (D)

Simpson's index is the probability that two individuals drawn at random belong to the same species. It is dominance-weighted: common species drive the value.

```
D       = Σ p_i^2                 (Simpson's dominance / concentration)
1 - D   = 1 - Σ p_i^2             (Gini–Simpson; probability two individuals differ)
1 / D   = 1 / Σ p_i^2             (inverse Simpson; an effective number of species)
```

```python
def simpson_concentration(quantities):
    n = np.asarray(quantities, dtype=float)
    n = n[n > 0]
    if n.sum() == 0:
        return 0.0
    p = n / n.sum()
    return np.sum(p ** 2)          # D

def gini_simpson(quantities):
    return 1 - simpson_concentration(quantities)   # 1 - D

def inverse_simpson(quantities):
    D = simpson_concentration(quantities)
    return 1 / D if D > 0 else 0.0                  # 1 / D
```

**Interpretation.** Be explicit about which form you report, because "Simpson index" is ambiguous in the literature:

| Form | Range | Higher value means |
|------|-------|--------------------|
| `D` (concentration) | 0–1 | more dominance, less diversity |
| `1 - D` (Gini–Simpson) | 0–1 | more diversity |
| `1 / D` (inverse Simpson) | 1–S | more diversity (in species-equivalents) |

The skill's `calculate_diversity_metrics()` reports `1 - D` as `simpson_index`. Simpson-family indices are relatively insensitive to rare species, making them robust when rare-species detection is uncertain.

## Pielou's Evenness (J')

Evenness rescales Shannon diversity by its maximum, isolating the equitability of the abundance distribution from richness.

```
J' = H' / ln(S)        (defined for S > 1; J' = 0 or undefined for S = 1)
```

```python
def pielou_evenness(quantities):
    n = np.asarray(quantities, dtype=float)
    n = n[n > 0]
    S = len(n)
    if S <= 1:
        return 0.0
    H = shannon(n)
    return H / np.log(S)
```

**Interpretation.** `J'` ranges 0–1: 1.0 means all species are equally abundant; values near 0 mean one or a few species dominate. Because `J'` removes the richness component, a community can be species-rich yet uneven (low `J'`) when one species — e.g., a schooling planktivore — overwhelms the count. Report `J'` alongside `S` so the two components of diversity are visible separately.

## Hill Numbers / Effective Number of Species

Hill numbers (`^q D`) unify richness, Shannon, and Simpson into a single family indexed by the order `q`, which controls how much weight rare species receive. All are expressed in the same intuitive unit — the **effective number of species**: the number of equally abundant species that would produce the observed diversity value.

```
^q D = ( Σ p_i^q )^( 1 / (1 - q) )        for q ≠ 1
^1 D = exp( -Σ p_i * ln(p_i) ) = exp(H')   as q → 1
```

| Order `q` | Name | Relationship | Sensitivity |
|-----------|------|--------------|-------------|
| `q = 0` | Richness | `^0 D = S` | counts all species equally (rare species fully weighted) |
| `q = 1` | Shannon diversity | `^1 D = exp(H')` | weights species by frequency |
| `q = 2` | Simpson diversity | `^2 D = 1 / Σ p_i^2 = 1/D` | favors dominant species |

```python
def hill_number(quantities, q):
    n = np.asarray(quantities, dtype=float)
    n = n[n > 0]
    if n.sum() == 0:
        return 0.0
    p = n / n.sum()
    if q == 1:
        return np.exp(-np.sum(p * np.log(p)))   # exp(H')
    return np.sum(p ** q) ** (1 / (1 - q))
```

**Interpretation.** Because Hill numbers share a common unit, they are directly comparable across orders and communities, and differences are linear (a community with `^1 D = 20` is twice as diverse as one with `^1 D = 10`). Reporting the trio `^0 D`, `^1 D`, `^2 D` gives a "diversity profile" that shows whether differences between sites are driven by rare species (`q = 0`) or by the dominant ones (`q = 2`). This is the recommended way to report diversity in community comparisons and is preferable to comparing raw `H'` values directly.

## Rarefaction

Richness rises with sampling effort, so two samples can only be compared at equal effort. Rarefaction estimates the expected richness if every sample were reduced to a common number of individuals (individual-based) or transects (sample-based), allowing fair comparison.

```
E[S_m] = Σ_i [ 1 - C(N - n_i, m) / C(N, m) ]
```

Where `E[S_m]` is the expected number of species in a random subsample of `m` individuals drawn from a community of `N` individuals, and `C(·,·)` is the binomial coefficient. The curve `E[S_m]` vs `m` is the rarefaction curve.

```python
from scipy.special import comb

def rarefaction(quantities, m):
    """Expected species richness in a subsample of m individuals (Hurlbert)."""
    n = np.asarray(quantities, dtype=float)
    n = n[n > 0]
    N = n.sum()
    if m > N:
        return np.nan                       # cannot rarefy beyond observed N
    denom = comb(N, m)
    expected = sum(1 - comb(N - ni, m) / denom for ni in n)
    return expected
```

**Interpretation.** Compare richness by reading all samples at the same `m` (commonly the smallest sample's total, so no sample is extrapolated). Rarefaction *interpolates* down to `m ≤ N`; estimating richness beyond the observed `N` requires extrapolation or asymptotic estimators (e.g., Chao1), which is a separate procedure. In the LTEM workflow, rarefy to a common number of transects when reefs differ in replication, consistent with the transect-as-sampling-unit rule in `SKILL.md`.

## Choosing and Reporting Indices

| Question | Recommended metric |
|----------|--------------------|
| How many species are here? | Richness `S` (with rarefaction if effort differs) |
| Overall diversity, common + rare | Shannon `H'` or `^1 D = exp(H')` |
| Diversity driven by dominant species | Inverse Simpson `1/D` (= `^2 D`) |
| Is abundance evenly spread? | Pielou's `J'` |
| Comparable, interpretable units | Hill numbers `^0 D`, `^1 D`, `^2 D` |

**Reporting checklist:**
- State the log base for `H'` (the skill uses natural log → nats).
- State which Simpson form (`D`, `1 - D`, or `1/D`) you report.
- Aggregate with SUM-then-MEAN to the transect level before computing indices.
- Equalize sampling effort, or use rarefaction, before comparing richness.
- Prefer Hill numbers (effective species) for cross-site or cross-year comparisons.

## Worked Integration with the Skill Workflow

The skill computes richness, Shannon, Simpson (`1 - D`), and Pielou's `J'` per survey in `calculate_diversity_metrics()`. To extend that output with Hill numbers for a diversity profile:

```python
def diversity_profile(group):
    q = group['quantity'].values
    return pd.Series({
        'richness_q0':  hill_number(q, 0),   # = S
        'shannon_q1':   hill_number(q, 1),   # = exp(H')
        'simpson_q2':   hill_number(q, 2),   # = 1/D
        'pielou_J':     pielou_evenness(q),
    })

profiles = survey_df.groupby('survey_id').apply(diversity_profile).reset_index()
```

Merge `profiles` back onto the survey metadata (`region`, `reef`, `year`, `depth`, `protection_status`) exactly as the diversity DataFrame is merged in the Core Workflow, then summarize by region or depth for community comparison and reporting.
