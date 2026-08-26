---
name: marine-species-analysis
domain: [biodiversity, biogeography]
data-source: [OBIS]
output-type: [analysis, model]
tags: [sdm, occurrence, habitat-suitability, maxent, obis]
peer_reviewed: true
status: stable
version: 0.2.0
description: This skill should be used when analyzing marine species distributions, accessing OBIS (Ocean Biodiversity Information System) data, building species distribution models (SDMs), or creating marine biodiversity maps. It provides workflows for downloading occurrence data, preparing environmental predictors, fitting MaxEnt or other SDM algorithms, and visualizing predicted habitat suitability. Use this skill when the user asks about species distributions, biodiversity data, OBIS queries, or habitat modeling.
---

# Marine Species Distribution Analysis

## Purpose

This skill guides the analysis of marine species distributions using Python in chatMPA Studio. It helps marine scientists:
- Access occurrence data from OBIS and GBIF
- Prepare environmental predictor variables
- Build and evaluate species distribution models
- Create habitat suitability maps
- Identify important marine areas for conservation

## When to Use This Skill

Use this skill when:
- User wants to download species occurrence data from OBIS
- User asks about species distribution modeling (SDM)
- User needs to create habitat suitability maps
- User wants to analyze biodiversity patterns
- User mentions MaxEnt, presence-only data, or niche modeling

Do NOT use this skill for:
- Reef ecology surveys (use `reef-ecology-report`)
- Temperature analysis (use `sea-surface-temperature`)
- Population genetics or phylogenetics

## Core Workflow

### 1. Set Up Environment

```python
# Core packages for species analysis
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd

# For OBIS data access
# pip install pyobis
from pyobis import occurrences, taxa

# For species distribution modeling
# pip install scikit-learn
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report

# For mapping
import cartopy.crs as ccrs
import cartopy.feature as cfeature
```

### 2. Access OBIS Data

```python
# Search for species
def search_species(scientific_name):
    """Search OBIS for species taxonomy."""
    result = taxa.search(q=scientific_name)
    return pd.DataFrame(result)

# Get occurrence records
def get_occurrences(taxon_id, geometry=None, startdate=None, enddate=None):
    """
    Download occurrence records from OBIS.

    Args:
        taxon_id: OBIS taxon ID (AphiaID)
        geometry: WKT polygon for spatial filter
        startdate: Start date (YYYY-MM-DD)
        enddate: End date (YYYY-MM-DD)
    """
    occ = occurrences.search(
        taxonid=taxon_id,
        geometry=geometry,
        startdate=startdate,
        enddate=enddate
    )
    return pd.DataFrame(occ)

# Example: Get sea turtle occurrences
turtle_taxa = search_species("Chelonia mydas")
print(turtle_taxa[['scientificName', 'taxonID', 'records']])

# Get occurrences
turtle_id = turtle_taxa['taxonID'].iloc[0]
turtle_occ = get_occurrences(
    taxon_id=turtle_id,
    startdate="2020-01-01",
    enddate="2024-12-31"
)
print(f"Found {len(turtle_occ)} occurrences")
```

### 3. Clean Occurrence Data

```python
def clean_occurrences(df):
    """
    Clean and filter occurrence data for SDM.

    Removes:
    - Records without coordinates
    - Duplicate locations
    - Records on land (optional)
    - Coordinate precision issues
    """
    clean = df.copy()

    # Remove missing coordinates
    clean = clean.dropna(subset=['decimalLongitude', 'decimalLatitude'])

    # Remove duplicates
    clean = clean.drop_duplicates(subset=['decimalLongitude', 'decimalLatitude'])

    # Filter by coordinate precision
    if 'coordinateUncertaintyInMeters' in clean.columns:
        clean = clean[clean['coordinateUncertaintyInMeters'] < 10000]

    # Remove terrestrial records (basic check)
    clean = clean[
        (clean['decimalLatitude'] >= -90) & (clean['decimalLatitude'] <= 90) &
        (clean['decimalLongitude'] >= -180) & (clean['decimalLongitude'] <= 180)
    ]

    print(f"Cleaned: {len(df)} -> {len(clean)} records")
    return clean

clean_occ = clean_occurrences(turtle_occ)
```

### 4. Prepare Environmental Data

```python
import xarray as xr

def extract_env_values(occurrences, env_data, lon_col='decimalLongitude', lat_col='decimalLatitude'):
    """
    Extract environmental values at occurrence locations.

    Args:
        occurrences: DataFrame with coordinates
        env_data: xarray Dataset with environmental layers
        lon_col, lat_col: Column names for coordinates

    Returns:
        DataFrame with environmental values added
    """
    result = occurrences.copy()

    for var in env_data.data_vars:
        values = []
        for _, row in occurrences.iterrows():
            val = env_data[var].sel(
                longitude=row[lon_col],
                latitude=row[lat_col],
                method='nearest'
            ).values
            values.append(float(val))
        result[var] = values

    return result

# Common environmental predictors for marine species:
# - Sea Surface Temperature (SST)
# - Salinity
# - Depth/Bathymetry
# - Chlorophyll-a (productivity)
# - Current velocity
# - Distance to coast
```

### 5. Generate Background Points

```python
def generate_background_points(n_points, extent, mask=None):
    """
    Generate random background (pseudo-absence) points.

    Args:
        n_points: Number of points to generate
        extent: [lon_min, lon_max, lat_min, lat_max]
        mask: Optional ocean mask (xarray DataArray)
    """
    np.random.seed(42)

    points = []
    while len(points) < n_points:
        lon = np.random.uniform(extent[0], extent[1])
        lat = np.random.uniform(extent[2], extent[3])

        if mask is not None:
            # Check if point is in ocean
            val = mask.sel(longitude=lon, latitude=lat, method='nearest').values
            if np.isnan(val):  # Ocean typically has NaN for land
                continue

        points.append({'longitude': lon, 'latitude': lat})

    return pd.DataFrame(points)

# Generate 10x presence points as background
n_background = len(clean_occ) * 10
extent = [-100, -60, 10, 35]  # Caribbean region
background = generate_background_points(n_background, extent)
background['presence'] = 0

# Add presence label to occurrences
presence = clean_occ[['decimalLongitude', 'decimalLatitude']].copy()
presence.columns = ['longitude', 'latitude']
presence['presence'] = 1

# Combine
all_points = pd.concat([presence, background], ignore_index=True)
```

### 6. Build Species Distribution Model

```python
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import roc_curve, auc

def build_sdm(data, env_vars, presence_col='presence'):
    """
    Build a species distribution model using Random Forest.

    Returns:
        Trained model, feature importances, AUC score
    """
    # Prepare features and target
    X = data[env_vars].dropna()
    y = data.loc[X.index, presence_col]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Train model
    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=10,
        min_samples_split=10,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc_score = roc_auc_score(y_test, y_pred_proba)

    # Feature importance
    importance = pd.DataFrame({
        'variable': env_vars,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='roc_auc')

    print(f"Test AUC: {auc_score:.3f}")
    print(f"CV AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std()*2:.3f})")

    return model, importance, auc_score

# Example usage
env_vars = ['sst', 'salinity', 'depth', 'chlorophyll']
model, importance, auc = build_sdm(all_points, env_vars)
print("
Variable Importance:")
print(importance)
```

### 7. Create Habitat Suitability Map

```python
def predict_habitat_suitability(model, env_data, env_vars):
    """
    Predict habitat suitability across study area.

    Args:
        model: Trained SDM
        env_data: xarray Dataset with environmental predictors
        env_vars: List of variable names

    Returns:
        xarray DataArray with suitability predictions
    """
    # Create prediction grid
    lons = env_data.longitude.values
    lats = env_data.latitude.values

    # Extract environmental values for all grid cells
    predictions = np.zeros((len(lats), len(lons)))

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            values = [env_data[var].sel(longitude=lon, latitude=lat).values
                     for var in env_vars]
            if any(np.isnan(values)):
                predictions[i, j] = np.nan
            else:
                predictions[i, j] = model.predict_proba([values])[0, 1]

    # Create xarray DataArray
    suitability = xr.DataArray(
        predictions,
        dims=['latitude', 'longitude'],
        coords={'latitude': lats, 'longitude': lons},
        name='suitability'
    )

    return suitability

# Generate predictions
suitability = predict_habitat_suitability(model, env_data, env_vars)
```

### 8. Visualize Results

```python
# Habitat suitability map
fig = plt.figure(figsize=(14, 10))
ax = plt.axes(projection=ccrs.PlateCarree())

# Plot suitability
im = ax.pcolormesh(
    suitability.longitude, suitability.latitude, suitability,
    transform=ccrs.PlateCarree(),
    cmap='RdYlGn', vmin=0, vmax=1
)

# Add occurrence points
ax.scatter(
    clean_occ['decimalLongitude'], clean_occ['decimalLatitude'],
    c='blue', s=5, alpha=0.5, transform=ccrs.PlateCarree(),
    label='Occurrences'
)

# Map features
ax.coastlines(resolution='10m')
ax.add_feature(cfeature.LAND, facecolor='lightgray')
ax.gridlines(draw_labels=True)

# Colorbar
cbar = plt.colorbar(im, ax=ax, shrink=0.6, label='Habitat Suitability')

ax.set_title('Predicted Habitat Suitability')
ax.legend(loc='lower right')
plt.savefig('habitat_suitability.png', dpi=300, bbox_inches='tight')

# Variable importance plot
fig, ax = plt.subplots(figsize=(10, 6))
importance.plot(kind='barh', x='variable', y='importance', ax=ax, legend=False)
ax.set_xlabel('Importance')
ax.set_title('Variable Importance in SDM')
plt.tight_layout()
plt.savefig('variable_importance.png', dpi=300)

# ROC curve
fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
roc_auc = auc(fpr, tpr)

fig, ax = plt.subplots(figsize=(8, 8))
ax.plot(fpr, tpr, color='blue', lw=2, label=f'ROC (AUC = {roc_auc:.2f})')
ax.plot([0, 1], [0, 1], 'k--', lw=2)
ax.set_xlabel('False Positive Rate')
ax.set_ylabel('True Positive Rate')
ax.set_title('ROC Curve')
ax.legend(loc='lower right')
plt.savefig('roc_curve.png', dpi=300)
```

## Data Sources

### Occurrence Data
| Source | URL | Best For |
|--------|-----|----------|
| OBIS | https://obis.org | Marine species globally |
| GBIF | https://gbif.org | All biodiversity |
| FishBase | https://fishbase.org | Fish species |
| SeaLifeBase | https://sealifebase.org | Non-fish marine life |

### Environmental Predictors
| Variable | Source | Resolution |
|----------|--------|------------|
| SST | NOAA OISST | 0.25° |
| Salinity | Copernicus | 0.25° |
| Bathymetry | GEBCO | 15 arc-sec |
| Chlorophyll | NASA MODIS | 4 km |
| Currents | HYCOM | 0.08° |

## Model Evaluation Guidelines

### AUC Interpretation
- 0.5 = Random (no skill)
- 0.6-0.7 = Poor
- 0.7-0.8 = Fair
- 0.8-0.9 = Good
- 0.9-1.0 = Excellent

### Best Practices
1. Use at least 10x background points vs presences
2. Include 5-10 environmental predictors maximum
3. Check for multicollinearity (VIF < 5)
4. Validate with independent data when possible
5. Report uncertainty in predictions

## Scripts Reference

### `scripts/download_obis.sh`
Downloads occurrence data from OBIS API.

```bash
./scripts/download_obis.sh --species "Chelonia mydas" --region caribbean
```

### Preparing Predictor Layers (inline)

There is no helper script for predictors — prepare them inline. Download marine layers
from Bio-ORACLE or MARSPEC, then crop and align every layer to the same study extent,
resolution, and CRS before modeling. See `references/predictor_selection.md` for variable
choice and collinearity screening.

**Option A — gdalwarp** (fast, for GeoTIFF/raster files). Crop and resample each layer to
a common grid (extent `-100 10 -60 35`, 0.1° cells):

```bash
# Repeat per layer (sst.tif, salinity.tif, bathymetry.tif, chlorophyll.tif ...)
for layer in sst salinity bathymetry chlorophyll; do
  gdalwarp -overwrite -t_srs EPSG:4326 \
    -te -100 10 -60 35 -tr 0.1 0.1 -r bilinear \
    "raw/${layer}.tif" "predictors/${layer}.tif"
done
```

**Option B — Python (rasterio + xarray/rioxarray)** to crop, regrid, and stack into one
aligned dataset:

```python
import glob, os
import rioxarray  # registers .rio accessor
import xarray as xr

extent = dict(minx=-100, miny=10, maxx=-60, maxy=35)  # [lon_min, lat_min, lon_max, lat_max]

layers = {}
ref = None
for path in sorted(glob.glob("raw/*.tif")):
    name = os.path.splitext(os.path.basename(path))[0]
    da = rioxarray.open_rasterio(path, masked=True).squeeze("band", drop=True)
    da = da.rio.clip_box(**extent)                # crop to study extent
    if ref is None:
        ref = da                                  # first layer defines target grid
    else:
        da = da.rio.reproject_match(ref)          # align CRS/resolution/extent
    layers[name] = da

predictors = xr.Dataset(layers)                   # all variables on one aligned grid
predictors = predictors.rename({"x": "longitude", "y": "latitude"})
predictors.to_netcdf("predictors/env_stack.nc")
```

Bio-ORACLE layers can also be downloaded in R via the `sdmpredictors` package; MARSPEC
ships standard rasters. Always confirm all layers share an identical grid before extracting
values at occurrence points.

## References

- **`references/obis_guide.md`** - OBIS API usage and data cleaning
- **`references/sdm_methods.md`** - SDM algorithm comparison
- **`references/predictor_selection.md`** - Environmental variable selection

## Success Criteria

A successful species distribution analysis includes:
- [ ] Occurrence data downloaded and cleaned
- [ ] Background points generated appropriately
- [ ] Environmental predictors extracted
- [ ] SDM fitted and evaluated (AUC reported)
- [ ] Habitat suitability map created
- [ ] Variable importance analyzed
- [ ] Results exported and documented
