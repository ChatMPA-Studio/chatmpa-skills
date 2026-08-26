---
name: sea-surface-temperature
domain: [oceanography, climate]
data-source: [ERDDAP]
output-type: [analysis]
tags: [sst, thermal-stress, dhw, anomaly, remote-sensing]
peer_reviewed: true
status: stable
version: 0.2.0
description: This skill should be used when analyzing sea surface temperature (SST) data, downloading oceanographic data from ERDDAP servers, creating temperature anomaly maps, or studying ocean warming patterns. It provides workflows for accessing remote sensing data, calculating thermal stress metrics (DHW, hotspots), and generating climate-relevant visualizations. Use this skill when the user asks about SST, ocean temperature, thermal stress, ERDDAP data, or satellite oceanography.
---

# Sea Surface Temperature Analysis

## Purpose

This skill guides the analysis of sea surface temperature (SST) data using Python in chatMPA Studio. It helps marine scientists:
- Download SST data from ERDDAP and other oceanographic servers
- Process and analyze temperature time series
- Calculate thermal stress metrics (Degree Heating Weeks, HotSpots)
- Create publication-quality maps and visualizations
- Identify warming trends and anomalies

## When to Use This Skill

Use this skill when:
- User wants to download SST data from ERDDAP
- User asks about ocean temperature patterns
- User needs to calculate thermal stress or bleaching alerts
- User wants to create SST maps or anomaly plots
- User mentions satellite oceanography or remote sensing temperature data

Do NOT use this skill for:
- Reef ecology surveys (use `reef-ecology-report`)
- Species distribution modeling (use `marine-species-analysis`)
- In-situ temperature logger data (general Python analysis)

## Core Workflow

### 1. Set Up Environment

```python
# Core packages for SST analysis
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import xarray as xr  # For NetCDF/gridded data

# For ERDDAP data access
# pip install erddapy
from erddapy import ERDDAP

# For mapping
# pip install cartopy
import cartopy.crs as ccrs
import cartopy.feature as cfeature
```

### 2. Access ERDDAP Data

ERDDAP servers provide access to oceanographic datasets. Common servers:

| Server | URL | Focus |
|--------|-----|-------|
| CoastWatch | https://coastwatch.pfeg.noaa.gov/erddap | Pacific, global SST |
| IOOS | https://erddap.ioos.us/erddap | US coastal |
| Copernicus | https://nrt.cmems-du.eu/erddap | European seas |

```python
# Connect to CoastWatch ERDDAP
e = ERDDAP(
    server="https://coastwatch.pfeg.noaa.gov/erddap",
    protocol="griddap"
)

# List available SST datasets
print("Searching for SST datasets...")
# Common dataset IDs:
# - jplMURSST41 : Multi-scale Ultra-high Resolution SST (1km)
# - erdMH1sstd1day : MODIS daily SST
# - nesdisVHNSQchlaDaily : Chlorophyll (for context)

# Set dataset
e.dataset_id = "jplMURSST41"

# Get dataset info
print(e.get_info_url())
```

### 3. Download SST Data

```python
# Define area of interest
e.constraints = {
    "time>=": "2024-01-01",
    "time<=": "2024-12-31",
    "latitude>=": 20.0,
    "latitude<=": 30.0,
    "longitude>=": -90.0,
    "longitude<=": -80.0,
}

# Select variables
e.variables = ["analysed_sst", "time", "latitude", "longitude"]

# Download as xarray Dataset
ds = e.to_xarray()
print(ds)

# Convert to Celsius if needed (MUR SST is in Kelvin)
if ds['analysed_sst'].max() > 100:  # Kelvin
    ds['sst_celsius'] = ds['analysed_sst'] - 273.15
else:
    ds['sst_celsius'] = ds['analysed_sst']
```

### 4. Calculate Climatology and Anomalies

```python
# Calculate monthly climatology
climatology = ds.groupby('time.month').mean('time')

# Calculate anomalies
ds['sst_anomaly'] = ds.groupby('time.month') - climatology

# Calculate Maximum Monthly Mean (MMM) - baseline for thermal stress
mmm = ds.groupby('time.month').mean('time').max('month')
ds['mmm'] = mmm['sst_celsius']
```

### 5. Thermal Stress Metrics

**HotSpot Calculation:**
```python
def calculate_hotspot(sst, mmm):
    """
    Calculate HotSpot (HS) - instantaneous thermal stress.

    HotSpot = SST - MMM (when SST > MMM, else 0)

    Args:
        sst: Current SST (xarray DataArray)
        mmm: Maximum Monthly Mean climatology

    Returns:
        HotSpot values (0 = no stress)
    """
    hotspot = sst - mmm
    hotspot = hotspot.where(hotspot > 0, 0)
    return hotspot

ds['hotspot'] = calculate_hotspot(ds['sst_celsius'], ds['mmm'])
```

**Degree Heating Weeks (DHW):**
```python
def calculate_dhw(hotspots, window_weeks=12):
    """
    Calculate Degree Heating Weeks (DHW).

    DHW = Sum of HotSpots > 1°C over rolling 12-week window

    Bleaching thresholds:
    - DHW >= 4: Bleaching likely
    - DHW >= 8: Severe bleaching and mortality likely
    """
    # Only count HotSpots > 1°C
    hs_significant = hotspots.where(hotspots >= 1, 0)

    # Rolling 12-week (84-day) sum, converted to weeks
    dhw = hs_significant.rolling(time=84, center=False).sum() / 7

    return dhw

ds['dhw'] = calculate_dhw(ds['hotspot'])
```

### 6. Create Visualizations

**SST Map:**
```python
# Set up map projection
fig = plt.figure(figsize=(12, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

# Get single time slice
sst_slice = ds['sst_celsius'].isel(time=-1)

# Plot SST
im = ax.pcolormesh(
    ds.longitude, ds.latitude, sst_slice,
    transform=ccrs.PlateCarree(),
    cmap='RdYlBu_r',
    vmin=20, vmax=32
)

# Add features
ax.coastlines(resolution='10m')
ax.add_feature(cfeature.LAND, facecolor='lightgray')
ax.gridlines(draw_labels=True)

# Colorbar
cbar = plt.colorbar(im, ax=ax, shrink=0.6, label='SST (°C)')

ax.set_title(f"Sea Surface Temperature - {str(sst_slice.time.values)[:10]}")
plt.savefig('sst_map.png', dpi=300, bbox_inches='tight')
```

**DHW Bleaching Alert Map:**
```python
# Custom colormap for DHW alerts
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm

# NOAA Coral Reef Watch alert levels
dhw_levels = [0, 1, 4, 8, 12, 16]
dhw_colors = ['#FFFFFF', '#FFFF00', '#FFA500', '#FF0000', '#8B0000']
dhw_cmap = LinearSegmentedColormap.from_list('dhw', dhw_colors)
dhw_norm = BoundaryNorm(dhw_levels, dhw_cmap.N)

fig = plt.figure(figsize=(12, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

dhw_slice = ds['dhw'].isel(time=-1)
im = ax.pcolormesh(
    ds.longitude, ds.latitude, dhw_slice,
    transform=ccrs.PlateCarree(),
    cmap=dhw_cmap, norm=dhw_norm
)

ax.coastlines()
ax.add_feature(cfeature.LAND, facecolor='lightgray')

cbar = plt.colorbar(im, ax=ax, shrink=0.6, label='DHW (°C-weeks)')
cbar.set_ticks([0, 2, 4, 8, 12])

ax.set_title('Degree Heating Weeks - Coral Bleaching Alert')
plt.savefig('dhw_alert_map.png', dpi=300, bbox_inches='tight')
```

**Time Series:**
```python
# Spatial mean time series
sst_mean = ds['sst_celsius'].mean(dim=['latitude', 'longitude'])
dhw_max = ds['dhw'].max(dim=['latitude', 'longitude'])

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

# SST time series
ax1.plot(ds.time, sst_mean, 'b-', linewidth=0.5)
ax1.axhline(y=ds['mmm'].mean().values, color='r', linestyle='--', label='MMM')
ax1.set_ylabel('SST (°C)')
ax1.legend()
ax1.set_title('Sea Surface Temperature Time Series')

# DHW time series
ax2.fill_between(ds.time, 0, dhw_max, alpha=0.7, color='red')
ax2.axhline(y=4, color='orange', linestyle='--', label='Bleaching Alert')
ax2.axhline(y=8, color='darkred', linestyle='--', label='Severe Alert')
ax2.set_ylabel('DHW (°C-weeks)')
ax2.set_xlabel('Date')
ax2.legend()

plt.tight_layout()
plt.savefig('sst_timeseries.png', dpi=300)
```

### 7. Trend Analysis

```python
from scipy import stats

def calculate_sst_trend(ds, dim='time'):
    """Calculate linear warming trend."""
    # Convert time to numeric (years)
    time_numeric = (ds.time - ds.time[0]).astype('timedelta64[D]').astype(float) / 365.25

    # Fit linear regression for each grid cell
    def fit_trend(y):
        if np.isnan(y).all():
            return np.nan, np.nan
        mask = ~np.isnan(y)
        slope, intercept, r, p, se = stats.linregress(time_numeric[mask], y[mask])
        return slope, p

    # Apply across grid
    trends = xr.apply_ufunc(
        fit_trend,
        ds['sst_celsius'],
        input_core_dims=[['time']],
        output_core_dims=[[], []],
        vectorize=True
    )

    return trends[0], trends[1]  # slope (°C/year), p-value

warming_rate, p_values = calculate_sst_trend(ds)
print(f"Mean warming rate: {float(warming_rate.mean()):.3f} °C/year")
```

## Data Sources

### Primary ERDDAP Datasets

| Dataset ID | Resolution | Coverage | Best For |
|------------|-----------|----------|----------|
| jplMURSST41 | 1 km | Global | High-res regional analysis |
| erdMH1sstdmday | 4 km | Global | Long-term trends |
| ncdcOisst21Agg | 0.25° | Global | Climate analysis |

### Alternative Data Sources

- **NOAA Coral Reef Watch:** https://coralreefwatch.noaa.gov/
- **Copernicus Marine Service:** https://marine.copernicus.eu/
- **NASA PODAAC:** https://podaac.jpl.nasa.gov/

## Scripts Reference

### `scripts/fetch_sst.sh`
Downloads SST data for a specified region and time period.

```bash
./scripts/fetch_sst.sh --lat 20,30 --lon -90,-80 --start 2024-01-01 --end 2024-12-31
```

### `scripts/calculate_dhw.sh`
Runs DHW calculation pipeline.

```bash
./scripts/calculate_dhw.sh input.nc output_dhw.nc
```

## Thermal Stress Reference

| Alert Level | DHW Range | Expected Impact |
|-------------|-----------|-----------------|
| No Stress | 0-1 | Normal conditions |
| Watch | 1-4 | Bleaching possible |
| Warning | 4-8 | Bleaching likely |
| Alert 1 | 8-12 | Severe bleaching |
| Alert 2 | >12 | Mortality likely |

## References

- **`references/erddap_guide.md`** - Detailed ERDDAP query examples
- **`references/thermal_stress.md`** - DHW methodology and interpretation
- **`references/mapping_templates.md`** - Cartopy map examples

## Success Criteria

A successful SST analysis includes:
- [ ] Data downloaded from ERDDAP successfully
- [ ] Climatology calculated correctly
- [ ] Anomalies computed
- [ ] Thermal stress metrics (DHW, HotSpot) calculated
- [ ] At least 2 maps created (SST, DHW)
- [ ] Time series visualization
- [ ] Data exported for further analysis
