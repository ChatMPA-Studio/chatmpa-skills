# NRSI Methodology Reference

## Normalized Reef State Index (NRSI)

The NRSI quantifies the trophic health of a reef based on the relative biomass of three trophic level categories. It was developed for the Gulf of California LTEM monitoring program.

## Trophic Level Mapping

The LTEM database uses the `TrophicLevelF` column which contains categorical trophic level ranges:

| TrophicLevelF | NRSI Category | Abbreviation | Ecological Meaning |
|--------------|---------------|--------------|-------------------|
| `2-2.5` | Lower Trophic Level | LTL | Herbivores, detritivores (e.g. parrotfish, surgeonfish) |
| `2.5-3` | Consumer Trophic Level | CTL | Low-level omnivores and invertivores |
| `3-3.5` | Consumer Trophic Level | CTL | Mid-level predators |
| `3.5-4` | Consumer Trophic Level | CTL | Upper mid-level predators |
| `4-4.5` | Upper Trophic Level | UTL | Apex predators (e.g. groupers, jacks, sharks) |

All trophic levels not matching UTL or LTL are classified as CTL (Consumer Trophic Level).

## Formula

### Standard Formula

```
NRSI = (UTL + LTL - CTL) / (UTL + LTL + CTL)
```

Where UTL, LTL, and CTL are relative biomass proportions (summing to 100% within a transect).

### Conditional Rule

When herbivore/detritivore biomass (LTL) dominates the system:

```
If LTL > UTL + CTL:
    NRSI = UTL / (UTL + CTL)
```

This prevents artificially high NRSI values in systems where massive herbivore biomass inflates the numerator. The conditional focuses on whether apex predators are present relative to consumers.

## Computation Steps

1. **Classify** — Map each observation's TrophicLevelF to UTL, LTL, or CTL
2. **Sum per transect** — Sum biomass within each transect for each category
3. **Average per reef** — Average transect-level biomass per reef
4. **Compute relative biomass** — Calculate proportions: each category / total
5. **Apply formula** — Use standard formula, or conditional if LTL > UTL + CTL
6. **Average NRSI** — Mean of transect-level NRSI values per reef

## Interpretation Ranges

| NRSI Range | Category | Description |
|-----------|----------|-------------|
| 0.5 to 1.0 | Excellent | Reef dominated by apex predators and herbivores; healthy food web with strong top-down control |
| 0.0 to 0.5 | Good | Balanced trophic structure; all levels represented |
| -0.5 to 0.0 | Degraded | Mid-level consumers dominate; possible overfishing of top predators |
| -1.0 to -0.5 | Severely degraded | Almost no apex predator biomass; collapsed trophic structure typical of heavily fished reefs |

## Bootstrap Confidence Intervals

NRSI uncertainty is estimated via bootstrap resampling:

1. For each reef, collect all transect-level NRSI values
2. Resample with replacement (n = number of transects)
3. Compute mean of resampled values
4. Repeat 100-500 times
5. 95% CI = 2.5th and 97.5th percentiles of bootstrap distribution

If CI includes 0, the reef's trophic state is ambiguous.

## Key References

- The NRSI formula follows the approach used in the LTEM analysis scripts (04-full_trends_analysis.R, lines 1038-1075)
- Bootstrap methodology adapted from the `resample_mean()` function in the same R script
- Trophic level assignments are pre-computed in the database (`TrophicLevelF` column)
- Iglewicz, B. & Hoaglin, D. (1993). Volume 16: How to Detect and Handle Outliers. ASQC Quality Press.
