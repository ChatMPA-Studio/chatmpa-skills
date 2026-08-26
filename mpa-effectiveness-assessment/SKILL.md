---
name: mpa-effectiveness-assessment
domain: [conservation-policy]
data-source: [generic]
output-type: [analysis, report]
tags: [mpa, biodiversity-comparison, conservation-outcomes]
peer_reviewed: true
status: stable
version: 0.2.0
description: This skill should be used when assessing Marine Protected Area (MPA) effectiveness, comparing biodiversity inside vs outside MPAs, analyzing temporal trends in MPA performance, or evaluating conservation outcomes. It provides workflows for loading MPA boundary data, calculating biodiversity metrics, performing statistical comparisons, and generating assessment reports.
---

# MPA Effectiveness Assessment

## Purpose

This skill guides the assessment of Marine Protected Area effectiveness using Python in chatMPA Studio. It helps marine conservation scientists:
- Load MPA boundaries and species occurrence data
- Calculate biodiversity metrics inside and outside MPAs
- Analyze temporal trends in protected area performance
- Generate assessment reports with statistical analysis

## When to Use This Skill

Use this skill when:
- User wants to evaluate MPA effectiveness
- User asks about biodiversity inside vs outside protected areas
- User needs to assess conservation outcomes
- User mentions WDPA, MPA boundaries, or protected area analysis
- User wants to compare species richness or abundance across protection levels

Do NOT use this skill for:
- General species distribution modeling (use `marine-species-analysis`)
- Coral reef-specific surveys (use `reef-ecology-report`)
- Temperature or climate analysis (use `sea-surface-temperature`)

## Core Workflow

### 1. Set Up Environment

```python
# Core packages for MPA analysis
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon
import scipy.stats as stats

# Optional: for advanced spatial analysis
# pip install pyobis rasterio fiona
```

### 2. Load MPA Boundaries

**Data sources:**
- World Database on Protected Areas (WDPA)
- National MPA databases
- Custom GeoJSON files

```python
# Load MPA boundaries
mpas = gpd.read_file('mpa_boundaries.geojson')

# Or load from WDPA shapefile
# mpas = gpd.read_file('WDPA_marine.shp')

# Filter for marine protected areas
mpas = mpas[mpas['MARINE'] > 0]

# Preview
print(f"Loaded {len(mpas)} MPAs")
print(mpas[['NAME', 'DESIG_TYPE', 'REP_AREA', 'STATUS_YR']].head())
```

**Ask user for:**
- MPA data file or region of interest
- Protection level categories (if available)
- Time period for establishment

### 3. Load Species Occurrence Data

```python
# Load occurrence records (from OBIS, GBIF, or local surveys)
occurrences = pd.read_csv('species_occurrences.csv')

# Create GeoDataFrame from coordinates
geometry = [Point(xy) for xy in zip(occurrences['longitude'], occurrences['latitude'])]
occurrences_gdf = gpd.GeoDataFrame(occurrences, geometry=geometry, crs='EPSG:4326')

print(f"Loaded {len(occurrences_gdf)} occurrence records")
print(f"Species: {occurrences_gdf['species'].nunique()}")
```

### 4. Spatial Join: Inside vs Outside MPA

```python
# Ensure same CRS
mpas = mpas.to_crs('EPSG:4326')
occurrences_gdf = occurrences_gdf.to_crs('EPSG:4326')

# Spatial join: identify points inside MPAs
inside_mpa = gpd.sjoin(occurrences_gdf, mpas, how='left', predicate='within')

# Create protection status column
inside_mpa['protected'] = inside_mpa['index_right'].notna()

# Summary
print(f"Inside MPA: {inside_mpa['protected'].sum()}")
print(f"Outside MPA: {(~inside_mpa['protected']).sum()}")
```

### 5. Calculate Biodiversity Metrics

```python
def calculate_biodiversity_metrics(df, group_col='protected'):
    """Calculate biodiversity metrics by protection status."""

    metrics = {}
    for group, data in df.groupby(group_col):
        # Species richness
        richness = data['species'].nunique()

        # Abundance
        abundance = len(data)

        # Shannon diversity
        species_counts = data['species'].value_counts()
        proportions = species_counts / species_counts.sum()
        shannon = -np.sum(proportions * np.log(proportions))

        # Simpson's diversity
        simpson = 1 - np.sum(proportions ** 2)

        metrics[group] = {
            'species_richness': richness,
            'total_abundance': abundance,
            'shannon_diversity': round(shannon, 3),
            'simpson_diversity': round(simpson, 3)
        }

    return pd.DataFrame(metrics).T

# Calculate metrics
metrics_df = calculate_biodiversity_metrics(inside_mpa, 'protected')
print("
Biodiversity Metrics by Protection Status:")
print(metrics_df)
```

### 6. Statistical Comparison

```python
# Prepare data for comparison
inside_records = inside_mpa[inside_mpa['protected']]
outside_records = inside_mpa[~inside_mpa['protected']]

# Species richness per site (if site info available)
def richness_by_site(df, site_col='site_id'):
    return df.groupby(site_col)['species'].nunique()

inside_richness = richness_by_site(inside_records)
outside_richness = richness_by_site(outside_records)

# Mann-Whitney U test (non-parametric)
stat, p_value = stats.mannwhitneyu(inside_richness, outside_richness, alternative='greater')
print(f"
Mann-Whitney U Test (Inside > Outside):")
print(f"  Statistic: {stat:.2f}")
print(f"  P-value: {p_value:.4f}")
print(f"  Significant (p < 0.05): {p_value < 0.05}")

# Effect size (Cliff's delta)
def cliffs_delta(x, y):
    n1, n2 = len(x), len(y)
    dominance = sum(1 if xi > yi else -1 if xi < yi else 0
                   for xi in x for yi in y)
    return dominance / (n1 * n2)

delta = cliffs_delta(inside_richness.values, outside_richness.values)
print(f"  Cliff's delta (effect size): {delta:.3f}")
```

### 7. Create Visualizations

```python
# Set ocean color palette
ocean_colors = ['#0077B6', '#00ABC8', '#90E0EF', '#CAF0F8']

fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# 1. Species richness comparison
ax1 = axes[0, 0]
metrics_df['species_richness'].plot(kind='bar', ax=ax1, color=ocean_colors[:2])
ax1.set_xlabel('Protection Status')
ax1.set_ylabel('Species Richness')
ax1.set_title('Species Richness: Inside vs Outside MPAs')
ax1.set_xticklabels(['Outside MPA', 'Inside MPA'], rotation=0)

# 2. Diversity indices comparison
ax2 = axes[0, 1]
diversity_metrics = metrics_df[['shannon_diversity', 'simpson_diversity']].T
diversity_metrics.plot(kind='bar', ax=ax2, color=ocean_colors[:2])
ax2.set_ylabel('Diversity Index')
ax2.set_title('Diversity Indices: Inside vs Outside MPAs')
ax2.legend(['Outside MPA', 'Inside MPA'])
ax2.set_xticklabels(['Shannon', 'Simpson'], rotation=0)

# 3. Boxplot of site-level richness
ax3 = axes[1, 0]
data_for_box = [outside_richness.values, inside_richness.values]
bp = ax3.boxplot(data_for_box, labels=['Outside MPA', 'Inside MPA'], patch_artist=True)
for patch, color in zip(bp['boxes'], ocean_colors[:2]):
    patch.set_facecolor(color)
ax3.set_ylabel('Species Richness per Site')
ax3.set_title(f'Site-Level Richness (p = {p_value:.4f})')

# 4. Map of MPAs and occurrences
ax4 = axes[1, 1]
mpas.plot(ax=ax4, color='lightblue', edgecolor='darkblue', alpha=0.5, label='MPAs')
inside_mpa[inside_mpa['protected']].plot(ax=ax4, color='green', markersize=5, alpha=0.5, label='Inside MPA')
inside_mpa[~inside_mpa['protected']].plot(ax=ax4, color='red', markersize=5, alpha=0.5, label='Outside MPA')
ax4.set_title('Occurrence Records by Protection Status')
ax4.legend()

plt.tight_layout()
plt.savefig('mpa_effectiveness_analysis.png', dpi=300, bbox_inches='tight')
plt.show()
```

### 8. Temporal Analysis (if data available)

```python
def temporal_trend_analysis(df, year_col='year', protected_col='protected'):
    """Analyze temporal trends in biodiversity by protection status."""

    # Richness by year and protection status
    temporal = df.groupby([year_col, protected_col])['species'].nunique().unstack()

    # Plot temporal trends
    fig, ax = plt.subplots(figsize=(12, 6))
    temporal.plot(ax=ax, marker='o')
    ax.set_xlabel('Year')
    ax.set_ylabel('Species Richness')
    ax.set_title('Temporal Trend in Species Richness by Protection Status')
    ax.legend(['Outside MPA', 'Inside MPA'])

    plt.savefig('mpa_temporal_trend.png', dpi=300, bbox_inches='tight')

    return temporal

# If year data available
# temporal_df = temporal_trend_analysis(inside_mpa)
```

### 9. Generate Report

```python
from datetime import datetime

# Compile report
report = f"""# MPA Effectiveness Assessment Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Tool:** chatMPA Studio

## Study Summary

- **MPAs Analyzed:** {len(mpas)}
- **Total Occurrence Records:** {len(inside_mpa)}
- **Records Inside MPAs:** {inside_mpa['protected'].sum()}
- **Records Outside MPAs:** {(~inside_mpa['protected']).sum()}
- **Total Species:** {inside_mpa['species'].nunique()}

## Biodiversity Metrics

{metrics_df.to_markdown()}

## Statistical Analysis

**Mann-Whitney U Test** (Inside > Outside):
- Test statistic: {stat:.2f}
- P-value: {p_value:.4f}
- Significant (α = 0.05): {"Yes" if p_value < 0.05 else "No"}
- Effect size (Cliff's delta): {delta:.3f}

## Key Findings

1. Species richness {"was significantly higher" if p_value < 0.05 else "did not significantly differ"} inside MPAs compared to outside (p = {p_value:.4f})
2. Shannon diversity index inside MPAs: {metrics_df.loc[True, 'shannon_diversity']:.3f}
3. Shannon diversity index outside MPAs: {metrics_df.loc[False, 'shannon_diversity']:.3f}

## Figures

![MPA Effectiveness Analysis](mpa_effectiveness_analysis.png)

## Recommendations

Based on this assessment:
{"- MPAs appear effective at conserving biodiversity in this region" if p_value < 0.05 and delta > 0 else "- Further investigation needed to assess MPA effectiveness"}
- Consider additional metrics (biomass, trophic structure) for comprehensive assessment
- Monitor temporal trends to track long-term effectiveness

---
*Generated with chatMPA Studio MPA Effectiveness Assessment Skill*
"""

# Save report
with open('mpa_effectiveness_report.md', 'w') as f:
    f.write(report)

print("Report saved to: mpa_effectiveness_report.md")
```

## Data Format Guidelines

### MPA Boundaries (GeoJSON/Shapefile)

| Field | Type | Description |
|-------|------|-------------|
| NAME | string | MPA name |
| DESIG_TYPE | string | Designation type |
| REP_AREA | float | Reported area (km²) |
| STATUS_YR | int | Year of establishment |
| MARINE | int | Marine coverage (0-2) |
| NO_TAKE | string | No-take status |
| geometry | polygon | MPA boundary |

### Occurrence Data (CSV)

| Column | Type | Description |
|--------|------|-------------|
| species | string | Scientific name |
| latitude | float | Latitude (WGS84) |
| longitude | float | Longitude (WGS84) |
| date | date | Observation date |
| year | int | Year of observation |
| site_id | string | Site identifier (optional) |
| abundance | int | Count (optional) |

## Common Analysis Patterns

### BACI Design (Before-After-Control-Impact)

```python
# For MPAs with known establishment dates
def baci_analysis(df, mpa_year, year_col='year', protected_col='protected'):
    df['period'] = df[year_col].apply(lambda x: 'After' if x >= mpa_year else 'Before')

    # Two-way ANOVA or similar
    # ...
```

### Distance-Based Analysis

```python
# Effect of distance from MPA boundary
from shapely.ops import nearest_points

def distance_to_mpa(point, mpa_boundary):
    return point.distance(mpa_boundary)
```

## Data Access Commands

These are inline, ready-to-run commands. No separate scripts are required.

### Download WDPA boundaries (Protected Planet)

The World Database on Protected Areas is distributed through Protected Planet
(https://www.protectedplanet.net). Download a country or global package
(shapefile / file-geodatabase / GeoJSON) from the site, or use the
Protected Planet API to fetch a specific protected area by WDPA ID.

```bash
# Country-level download page (browse and download the WDPA package):
#   https://www.protectedplanet.net/country/<ISO3>     e.g. .../country/MEX

# Protected Planet API: fetch a protected area record by WDPA ID (needs a free token)
curl "https://api.protectedplanet.net/v3/protected_areas/<WDPAID>?token=YOUR_TOKEN"
```

Then load and filter the downloaded polygons in Python:

```python
import geopandas as gpd
wdpa = gpd.read_file("WDPA_polygons.shp")          # or .gdb / .geojson
marine = wdpa[wdpa["MARINE"].isin(["1", "2"])]      # coastal + marine PAs
```

See `references/wdpa_fields.md` for the attribute schema.

### Query OBIS occurrences (REST API)

OBIS exposes a public REST API at https://api.obis.org. Query occurrences by
scientific name, a WKT `geometry` (bounding box or polygon), and a date range.
Results are JSON.

```bash
# Bounding box as WKT POLYGON (lon lat order): bbox -90,10 to -60,30
curl "https://api.obis.org/v3/occurrence?scientificname=Epinephelus%20striatus&geometry=POLYGON((-90%2010,-60%2010,-60%2030,-90%2030,-90%2010))&startdate=2010-01-01&enddate=2024-12-31" \
  -o occurrences.json
```

Or query directly from Python with the same parameters:

```python
import requests, pandas as pd
params = {
    "scientificname": "Epinephelus striatus",
    "geometry": "POLYGON((-90 10,-60 10,-60 30,-90 30,-90 10))",
    "startdate": "2010-01-01",
    "enddate": "2024-12-31",
}
r = requests.get("https://api.obis.org/v3/occurrence", params=params, timeout=120)
records = r.json()["results"]
df = pd.DataFrame(records)   # has decimalLongitude / decimalLatitude / scientificName
```

## References

Load these reference documents for detailed guidance:

- **`references/mpa_metrics.md`** - Standard MPA effectiveness metrics
- **`references/statistical_methods.md`** - Statistical testing approaches
- **`references/wdpa_fields.md`** - WDPA data field descriptions

## Success Criteria

A successful MPA effectiveness assessment includes:
- [ ] MPA boundaries loaded and visualized
- [ ] Species occurrence data loaded and georeferenced
- [ ] Spatial join completed (inside vs outside)
- [ ] Biodiversity metrics calculated
- [ ] Statistical comparison performed
- [ ] At least 4 visualizations created
- [ ] Assessment report generated
- [ ] Key findings documented
