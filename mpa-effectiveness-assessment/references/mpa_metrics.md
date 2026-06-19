# Standard MPA Effectiveness Metrics

Quantitative metrics used to evaluate whether a Marine Protected Area (MPA)
is delivering biodiversity and fisheries benefits relative to fished or
unprotected reference areas. Most effectiveness studies rest on a
**space-for-time** or **control-impact** contrast: assemblages inside the MPA
are compared with those at ecologically comparable sites outside.

## Core Response Variables

| Metric | Definition | Typical units |
|--------|-----------|---------------|
| Density | Individuals per unit area | ind. / 100 m² |
| Biomass | Mass per unit area (from length–weight relationships) | g or kg / 100 m² |
| Species richness | Number of species recorded per sample/site | count |
| Shannon diversity (H′) | `-Σ pᵢ ln pᵢ` over species proportions | nats |
| Simpson diversity | `1 − Σ pᵢ²` | unitless (0–1) |
| Mean body size | Average length, or mean of size distribution | cm |

Biomass is generally the most responsive and policy-relevant variable because
fishing removes large-bodied, high-value individuals first; recovery inside
no-take zones is expressed strongly through size and biomass before richness.

### Biomass from length data

Convert observed lengths (L) to mass with the allometric relationship
`W = a · L^b`, where `a` and `b` are species-specific length–weight
coefficients (e.g. from FishBase). Sum individual masses and divide by the
surveyed area to get areal biomass.

```python
df['weight_g'] = df['a'] * df['length_cm'] ** df['b']
biomass = df.groupby('transect_id')['weight_g'].sum() / transect_area_m2 * 100
```

## Inside-vs-Outside Comparison

Compute each metric separately for protected and reference samples, then
compare. Keep samples at a consistent spatial unit (transect, station, or
site mean) so replicates are independent and comparable.

| Step | Action |
|------|--------|
| 1 | Aggregate raw counts to a sampling unit (transect/site) |
| 2 | Compute the metric per unit |
| 3 | Summarize by protection status (mean ± SE, median, n) |
| 4 | Apply a statistical test (see `statistical_methods.md`) |
| 5 | Report an effect size, not just a p-value |

## Response Ratio

The **log response ratio (lnRR)** is the standard effect-size metric for
inside-vs-outside MPA contrasts and for meta-analysis across MPAs.

```
lnRR = ln( X_inside / X_outside )
```

where `X` is the mean of the response variable (e.g. biomass). Interpretation:

| lnRR | Back-transformed ratio | Meaning |
|------|------------------------|---------|
| 0 | 1.0 | No difference inside vs outside |
| 0.69 | 2.0 | Inside value double the outside value |
| 1.10 | 3.0 | Inside value triple the outside value |
| < 0 | < 1.0 | Lower inside than outside |

The simple (untransformed) **response ratio** `X_inside / X_outside` is also
widely reported. Log transformation is preferred because it is symmetric
around zero and its sampling distribution is closer to normal, which matters
when pooling many MPAs.

## Target vs Non-Target Species

A robust signal of fishing-driven protection effects is a **stronger response
in fished (target) species than in non-target species**. Split the assemblage
by exploitation status (commercial / recreationally targeted vs not) and
compute response ratios separately.

- Large response in targets + little response in non-targets → consistent with
  a fishing-mediated protection effect.
- Similar responses in both groups → effect may be driven by habitat, depth,
  or other confounds rather than protection itself.

Targeted-group classifications should come from a documented source (e.g. local
landings records or published trophic/fishery designations), not assumed.

## Trophic Structure

Protection often shifts community composition toward higher trophic levels as
predators and large-bodied species recover. Useful descriptors:

- **Trophic-group biomass** — biomass partitioned among piscivores,
  carnivores, herbivores, planktivores, etc.
- **Predator (top-predator) biomass or proportion** — frequently the clearest
  recovery signal in well-enforced no-take reserves.
- **Mean trophic level** of the assemblage, weighted by biomass.
- **Size spectrum / slope** — the slope of abundance against body-size class;
  fishing tends to steepen (more negative) the slope, and protection can relax it.

## Fishing-Pressure Context

Inside-vs-outside differences are only interpretable against the prevailing
fishing pressure. Without exploitation outside the MPA, there is little
"treatment contrast" to detect. Document the context:

- Outside-area fishing intensity (effort, gear, landings if available).
- MPA protection level and enforcement (no-take vs multi-use; see
  `wdpa_fields.md` `NO_TAKE`, `IUCN_CAT`).
- Time since establishment (`STATUS_YR`) — recovery is time-dependent, and
  biomass benefits typically accrue over years to decades.

## Interpretation Checklist

- [ ] Report effect sizes (lnRR / response ratio) with confidence intervals,
      not p-values alone.
- [ ] Confirm reference sites are ecologically comparable (habitat, depth,
      exposure) to the protected sites.
- [ ] Check whether target species respond more strongly than non-targets.
- [ ] Note time since protection and enforcement level.
- [ ] Distinguish *correlation* (inside differs from outside) from *causal
      effectiveness* (the difference is attributable to protection).
