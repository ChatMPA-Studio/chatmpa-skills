# Environmental Variable Selection

## Introduction

Predictor selection is one of the highest-leverage decisions in species distribution
modeling. Too few or irrelevant variables produce a weak model; too many or correlated
variables cause overfitting and unstable response curves. This guide covers choosing
ecologically relevant marine predictors, handling collinearity, matching spatial
resolution and extent, common data sources, and avoiding overfitting.

## Choosing Marine Predictors

Select variables that plausibly drive the species' physiology, behavior, or food supply,
not just whatever is available. Common categories for marine SDMs:

| Category | Example variables | Ecological rationale |
|----------|-------------------|----------------------|
| Thermal | SST (mean, min, max, range) | Sets metabolic and range limits |
| Salinity | Surface / bottom salinity | Osmoregulation; estuarine vs. oceanic |
| Topographic | Bathymetry, slope, distance to coast | Habitat depth zonation, structure |
| Productivity | Chlorophyll-a, primary production, nutrients | Proxy for food availability |
| Hydrodynamic | Current velocity, mixed-layer depth | Dispersal, larval transport |
| Chemical | Dissolved oxygen, pH | Tolerance limits, hypoxia |
| Light | PAR, turbidity | Photosynthesis-dependent habitats |

Guidance:
- Prefer variables with a mechanistic link to the species over convenient proxies.
- For benthic species use bottom-layer variables (bottom temperature, salinity, oxygen)
  rather than surface layers.
- Include both means and extremes when range limits are set by tolerance (e.g., max SST
  for thermal stress, min for cold edges).
- Keep the predictor count modest relative to sample size (see Overfitting below).

## Collinearity

Correlated predictors inflate variance, destabilize coefficients, and make variable
importance unreliable. Screen for collinearity before fitting.

### Correlation screening

Compute a pairwise correlation matrix (Pearson or Spearman) on predictor values sampled
across the study area and drop one of each pair exceeding a threshold (commonly |r| > 0.7),
keeping the more ecologically meaningful variable.

```python
import pandas as pd

# env_df: rows = sampled cells, columns = candidate predictors
corr = env_df.corr(method='spearman').abs()
# Inspect pairs with corr > 0.7 and drop redundant variables
high = corr.where(corr > 0.7)
```

### Variance Inflation Factor (VIF)

VIF measures how much a predictor is explained by the others. Iteratively drop the
highest-VIF variable until all remain below a threshold (commonly VIF < 5, stricter VIF < 3).

```python
import pandas as pd
from statsmodels.stats.outliers_influence import variance_inflation_factor

def reduce_by_vif(df, threshold=5.0):
    """Drop predictors one at a time until all VIF < threshold."""
    X = df.dropna().copy()
    while True:
        vifs = pd.Series(
            [variance_inflation_factor(X.values, i) for i in range(X.shape[1])],
            index=X.columns,
        )
        if vifs.max() < threshold:
            return list(X.columns), vifs
        X = X.drop(columns=vifs.idxmax())

kept, vifs = reduce_by_vif(env_df[candidate_vars])
print("Retained predictors:", kept)
```

## Spatial Resolution and Extent

### Resolution

- Match resolution to the species' mobility and the occurrence data precision: there is no
  benefit to 1 km predictors if occurrences are accurate only to ~10 km.
- All predictor layers must share the **same grid** (resolution, alignment, CRS) before
  modeling; resample/regrid to a common target.
- Finer is not always better: very fine grids increase compute and can introduce noise
  without ecological signal.

### Extent

- Define the study extent to cover the species' accessible range, not the entire ocean;
  an over-large extent inflates AUC and biases background sampling toward irrelevant
  environments.
- Restrict to plausible habitat (e.g., a depth or distance-to-coast limit, or a buffered
  convex hull around occurrences) so background contrasts reflect real availability.

## Data Sources

| Source | Variables | Native resolution | Notes |
|--------|-----------|-------------------|-------|
| Bio-ORACLE | SST, salinity, productivity, oxygen, pH, current, nutrients (surface & bottom) | ~5 arc-min (~9 km) | Purpose-built for marine SDM; present + future scenarios |
| MARSPEC | SST, salinity, bathymetry-derived topography | up to 30 arc-sec | High-resolution physical/topographic layers |
| GEBCO | Bathymetry | 15 arc-sec | Global depth grid; derive slope, distance to coast |
| Copernicus Marine | Physical & biogeochemical reanalysis | varies | Time-resolved fields |
| NOAA / NASA remote sensing | SST (OISST), chlorophyll (MODIS) | 0.25° / ~4 km | Satellite climatologies |

Bio-ORACLE and MARSPEC are the most common starting points because they provide
analysis-ready, aligned marine layers. Access Bio-ORACLE via the `sdmpredictors` R package
or its download API; MARSPEC layers are distributed as standard rasters.

## Avoiding Overfitting

1. **Limit predictor count relative to presences.** A common rule of thumb is at least
   ~10 occurrences per predictor; with few records, restrict to a handful of variables.
2. **Remove collinear predictors** (correlation / VIF) before fitting.
3. **Use regularization or smoothing controls** (MaxEnt regularization multiplier, GAM
   spline penalties, BRT learning rate, tree depth limits).
4. **Validate with spatial cross-validation** so reported skill reflects transferability,
   not autocorrelation.
5. **Check response curves** for ecological plausibility; reject variables producing
   biologically implausible shapes.
6. **Beware extrapolation** beyond the training environmental range; flag novel conditions
   (e.g., MESS / multivariate environmental similarity) when projecting to new areas or
   future climate.

## Workflow Summary

1. Assemble candidate predictors with a clear ecological rationale.
2. Crop and align all layers to a common grid and the chosen study extent.
3. Screen collinearity (correlation > 0.7, then VIF < 5) and reduce the set.
4. Keep the count modest relative to sample size.
5. Fit, evaluate with spatial CV, and inspect response curves.
6. Iterate, documenting why each variable was kept or dropped.
