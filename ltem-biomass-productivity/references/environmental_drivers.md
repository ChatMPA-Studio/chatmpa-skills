# Temperature and Chlorophyll Effects on Fish

This reference explains, conceptually, how sea-surface temperature (`mean_sst`)
and chlorophyll-a (`mean_chl`) relate to fish biomass and productivity. Use it
when interpreting the environmental-correlation, SST–biomass, and
chlorophyll–productivity steps of the LTEM workflow. It contains no dataset
values — only standard mechanisms and the directional expectations they imply.

## Two Pathways: Bottom-Up Energy vs. Thermal Physiology

Environmental variables act on fish through two broad, partly independent
pathways:

1. **Bottom-up (resource) control** — primarily indexed by chlorophyll-a.
   Energy availability at the base of the food web propagates up to fish.
2. **Thermal physiology** — primarily indexed by SST. Temperature governs
   metabolic and growth rates and sets distributional limits.

A given correlation between a fish metric and an environmental variable usually
reflects some combination of both pathways, which is why SST and chlorophyll
should be examined together rather than in isolation.

## Chlorophyll-a and Bottom-Up Control

Chlorophyll-a is a remote-sensing proxy for **phytoplankton biomass** and hence
for **primary productivity** at the base of the marine food web. The bottom-up
hypothesis predicts that greater primary production supports greater secondary
production, supporting in turn higher fish productivity and, over time, higher
fish biomass.

```
nutrients → phytoplankton (chl-a) → zooplankton/benthos → fish production → fish biomass
```

Directional expectations:

- **Chlorophyll-a vs. fish productivity (`prod`)** — typically **positive**.
  More basal energy supports faster growth and turnover. This is the most direct
  bottom-up signal and the reason the workflow pairs `mean_chl` with `total_prod`.
- **Chlorophyll-a vs. fish biomass** — often positive but usually **weaker and
  lagged** than the productivity relationship, because biomass accumulates over
  time and is also shaped by mortality, fishing, and protection history.

### Why log scaling is appropriate

Both chlorophyll-a and production span orders of magnitude and tend to relate
multiplicatively rather than additively. Productivity–chlorophyll relationships
are therefore conventionally examined on **log-log axes**, where a power-law
relationship appears linear:

```
log(P) = m * log(chl) + c        # slope m is the scaling exponent
```

This matches the log-log treatment in the chlorophyll–productivity workflow step.

### Caveats for chlorophyll

- Satellite chlorophyll integrates the near-surface layer and may not represent
  conditions at reef depth.
- Very high chlorophyll can indicate upwelling/eutrophic conditions whose other
  correlates (cold water, turbidity, hypoxia) may offset the energy benefit.
- The chlorophyll signal can be **lagged**: this season's production reflects
  recent food supply, while this year's biomass reflects cumulative past supply.

## Sea-Surface Temperature and Thermal Performance

Temperature is a master variable for ectotherms. Fish have no internal
temperature regulation, so SST directly sets the pace of metabolism, growth,
digestion, and activity.

### The thermal performance curve

Physiological performance (growth, metabolic scope) follows a **unimodal thermal
performance curve**: it rises with temperature to a species-specific **thermal
optimum (Topt)**, then falls steeply toward the upper thermal limit.

```
performance
    ^
    |        .-''-.
    |     .-'      '.
    |   .'           \
    | .'              \      (steep decline past Topt)
    +------------------------> temperature
        cold   Topt   warm
```

Implications for SST–biomass and SST–productivity analyses:

- The relationship is often **non-linear (hump-shaped)**, not strictly
  increasing or decreasing. A quadratic fit that beats the linear fit — and an
  implied optimal SST — is the expected signature of a thermal optimum. This is
  exactly why the workflow tests a quadratic SST model alongside the linear one.
- A **monotonic positive** SST relationship usually means the sampled thermal
  range sits below the optimum (warming still helps).
- A **monotonic negative** SST relationship usually means the sampled range sits
  above the optimum, or that warm-water sites carry other stressors.

### Direct vs. indirect temperature effects

| Effect type | Mechanism | Sign on fish metrics |
|-------------|-----------|----------------------|
| Direct (metabolic) | Warmer water raises growth/turnover within tolerance | Positive up to Topt, then negative |
| Direct (range limits) | Temperature sets where species can persist | Shifts community composition |
| Indirect (oxygen) | Warm water holds less dissolved O₂ while raising O₂ demand | Negative at high SST |
| Indirect (stratification) | Warming strengthens stratification, reducing nutrient supply and chlorophyll | Negative, via reduced bottom-up energy |

The indirect stratification effect creates a frequent **inverse coupling between
SST and chlorophyll**: warm, stratified water tends to be nutrient-poor and
low-chlorophyll, while cool, upwelling water tends to be productive. Because of
this, SST and chlorophyll are often negatively correlated with each other, and
their separate effects on fish can partly cancel. Interpreting either variable in
isolation is therefore risky — examine them jointly (e.g. colour SST–biomass
points by chlorophyll, as the workflow visualisation does).

## Tropicalization and Community Reorganization

Sustained warming does more than shift rates: it reorganizes assemblages.
Warm-affiliated, often smaller-bodied and lower-trophic species expand while
cool-affiliated species contract — a process commonly termed
**tropicalization**. Because body size and trophic level shape both biomass and
production (see `production_ecology.md`), warming-driven compositional change can
alter total biomass, mean body size, mean trophic level, and P/B even where no
single species' physiology has reached its limit. When SST correlates with
*community* metrics (mean size, mean trophic level, richness), suspect this
compositional pathway rather than a purely physiological one.

## Putting It Together: Expected Correlation Signs

These are *typical* expectations for interpretation, not guaranteed outcomes —
always report the observed values.

| Fish metric | vs. chlorophyll-a | vs. SST |
|-------------|-------------------|---------|
| Productivity (`prod`) | Positive (bottom-up) | Hump-shaped (optimum) |
| Biomass | Positive, weaker/lagged | Hump-shaped or context-dependent |
| Turnover / P/B | Positive (more energy → faster turnover) | Positive within tolerance |
| Mean body size | Weak / variable | Often negative under warming (small-bodied gain) |
| Mean trophic level | Variable | Often negative under tropicalization |
| Species richness | Variable | Often positive toward warm/tropical end (see latitudinal_gradients.md) |

## Statistical Cautions

- Use **transect-level totals** as the unit of correlation; raw rows cause
  pseudoreplication and inflate significance.
- Prefer **Spearman (rank) correlation** for these often non-linear,
  non-normal relationships, as the workflow does.
- A significant correlation is not a mechanism. SST, chlorophyll, latitude,
  depth, and protection are all spatially confounded in field data; distinguish
  them with multivariate models (e.g. the random-forest step) rather than from
  pairwise correlations alone.
- Watch for **collinearity** between SST and chlorophyll when both enter a model.
