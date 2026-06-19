# Fish Production and Turnover Theory

This reference explains the production-ecology concepts behind the `prod`,
`turnover`, and `biomass` variables used in the LTEM biomass workflow. Use it
when interpreting productivity results, choosing aggregation rules, or writing
the production-ecology sections of a report.

## Key Definitions

| Term | Symbol | Meaning |
|------|--------|---------|
| Standing biomass | B | Mass of live fish present per unit area at a point in time (here: ton/ha) |
| Somatic production | P | Rate at which new fish tissue (mass) is generated per unit area per unit time through individual growth |
| Production-to-biomass ratio | P/B | Production divided by standing biomass; an intrinsic turnover rate (per year) |
| Turnover | — | Replacement of biomass through growth, recruitment and loss; the inverse of P/B is the mean residence time of a unit of biomass |

**Somatic production** is biomass *flux*, not biomass *stock*. A reef can hold
high standing biomass with low production (large, slow-growing fish) or modest
biomass with high production (small, fast-growing fish). Reporting biomass alone
misses this distinction, which is why the LTEM dataset carries both `biomass` and
`prod`.

## Production-to-Biomass (P/B) Ratio

The P/B ratio is the central currency of production ecology:

```
P/B = P / B          # units: per year (yr^-1)
```

- **High P/B** — biomass turns over quickly; the assemblage is dominated by
  small, short-lived, fast-growing fish. Characteristic of productive,
  disturbance-prone, or heavily-exploited systems.
- **Low P/B** — biomass turns over slowly; dominated by large, long-lived,
  slow-growing fish. Characteristic of stable systems and accumulated standing
  stock (e.g. recovered predator biomass inside an effective MPA).

P/B tends to *decline* with increasing body size and increasing trophic level,
because larger and higher-trophic-level fish grow more slowly relative to their
mass. This is why the LTEM workflow weights `turnover` by `biomass` rather than
by abundance: turnover is a property of mass flux, not of individual counts.

### Mean residence time

The reciprocal of P/B is the average time a unit of biomass persists:

```
residence_time = 1 / (P/B)      # years
```

A reef with P/B = 2 yr^-1 replaces its biomass roughly every six months; a reef
with P/B = 0.3 yr^-1 takes a few years.

## How Individual Growth Drives Production

Somatic production at the individual level is the time-derivative of body mass.
Body mass relates to length through the standard allometric length–weight
relationship:

```
W = a * L^b
```

where `a` and `b` are species-specific parameters (b is typically near 3 for
isometric growth). Length itself increases through time following a
**von Bertalanffy growth function (VBGF)**:

```
L(t) = Linf * (1 - exp(-K * (t - t0)))
```

| Parameter | Meaning |
|-----------|---------|
| `Linf` | Asymptotic (maximum) length |
| `K` | Growth coefficient — how fast Linf is approached |
| `t0` | Theoretical age at zero length |

Production of an individual is its growth in mass per unit time, obtained by
combining the length–weight relationship with the growth rate `dL/dt` from the
VBGF (chain rule):

```
dW/dt = a * b * L^(b-1) * (dL/dt)
```

Summing individual production across all fish in a sample, then dividing by
survey area, gives areal production `P`. The LTEM `prod` column carries this
quantity at the row (species × size-class) level, which is why it must be
**summed within a transect**, exactly like `biomass`, before averaging across
transects.

## Estimating Production for Reef Fish from Survey Data

Underwater visual census data (counts by species and size class) support several
standard approaches to estimating production without ageing individual fish:

1. **Growth-parameter / size-based method.** For each observed fish, convert
   length to mass and use published VBGF parameters (`Linf`, `K`) to estimate the
   instantaneous somatic growth rate, hence individual production. Sum over all
   individuals and divide by area. This is the most common approach for reef-fish
   productivity from census data and underlies the LTEM `prod` variable.

2. **P/B-multiplier method.** Apply an empirically derived or modelled P/B ratio
   (often itself a function of body size, water temperature, and trophic level)
   to observed standing biomass: `P = (P/B) * B`. Useful for coarse, fast
   estimates when species-specific growth parameters are unavailable.

3. **Cohort / size-structured methods.** Where repeated surveys track size
   distributions through time, production can be inferred from the change in the
   size structure of the standing stock. Requires consistent time series.

All three depend on accurate length-to-mass conversion, so observer length
estimates and the choice of `a`, `b` parameters are the dominant sources of
uncertainty.

## Temperature Dependence of Production

Production is temperature-sensitive because growth and metabolism are
temperature-dependent processes. Within a species' tolerance range, warmer water
generally raises metabolic and growth rates, increasing P/B — up to a thermal
optimum, beyond which performance declines (see
`environmental_drivers.md`). Consequently, two reefs with identical standing
biomass can differ in production simply because of their thermal regime. When
correlating `prod` or `turnover` with `mean_sst`, expect (and check for) this
unimodal rather than strictly monotonic response.

## Trophic Structure and Production

Because P/B declines with trophic level, the *partitioning* of production across
trophic groups differs from the partitioning of biomass:

- Herbivores and planktivores (low trophic level, small-bodied) typically
  contribute a **disproportionately large share of production** relative to their
  share of biomass.
- Top predators (high trophic level, large-bodied) typically hold a large share
  of *biomass* but a smaller share of *production*.

This is why the LTEM trophic analysis sums both `biomass` and `prod` per trophic
group: the two tell complementary stories about ecosystem function.

## Interpretation Guide

| Pattern | Likely ecological reading |
|---------|---------------------------|
| High biomass, low P/B | Accumulated, slow-turnover stock (large/old fish; possible protection effect) |
| Low biomass, high P/B | Fast-turnover assemblage (small fish; productive or disturbed/exploited) |
| Production rises then falls with SST | Thermal-performance optimum within range |
| Production tracks chlorophyll-a | Bottom-up (resource) control of production |
| Herbivore production share > biomass share | Normal allometric expectation, not an anomaly |

## Aggregation Reminders (tie-in with SKILL.md)

- `biomass` and `prod` are **stocks/fluxes per row** → SUM within transect, then
  average across transects.
- `turnover` (P/B) is a **rate** → average directly, weighted by `biomass`.
- Never weight turnover by `quantity`; turnover is tied to mass, not counts.
- The number of **transects** is the sample size for any production statistic,
  not the number of raw rows.

## Caveats

- Production estimates inherit all uncertainty in length–weight and growth
  parameters; treat absolute values cautiously and emphasise relative
  comparisons.
- Production reflects *somatic growth* of observed standing stock; it does not by
  itself account for mortality, emigration, or reproductive (gonadal) output.
- Single-visit census production is an instantaneous snapshot; multi-year LTEM
  series are needed to characterise production trends.
