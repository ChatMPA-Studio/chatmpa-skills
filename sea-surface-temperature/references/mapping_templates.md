# Cartopy Map Examples

## Introduction

This reference collects runnable Cartopy templates for the maps this skill
produces: an SST map, an anomaly map, and a DHW bleaching-alert map. Each
snippet sets a projection, draws coastlines and land, adds gridlines and a
colorbar, and constrains the extent. They assume an xarray `Dataset` `ds` with
`latitude`/`longitude` coordinates, as built in `SKILL.md`.

## Common Imports

```python
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
```

## SST Map

`PlateCarree` is the simplest choice for regional lat/lon grids. Use a
single-time slice and a perceptually reasonable diverging-warm colormap.

```python
fig = plt.figure(figsize=(12, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

sst_slice = ds['sst_celsius'].isel(time=-1)

im = ax.pcolormesh(
    ds.longitude, ds.latitude, sst_slice,
    transform=ccrs.PlateCarree(),   # data CRS, always PlateCarree for lon/lat
    cmap='RdYlBu_r', vmin=20, vmax=32,
    shading='auto',
)

# Constrain to the area of interest: [lon_min, lon_max, lat_min, lat_max]
ax.set_extent([-90, -80, 20, 30], crs=ccrs.PlateCarree())

ax.add_feature(cfeature.LAND, facecolor='lightgray', zorder=2)
ax.coastlines(resolution='10m', linewidth=0.6, zorder=3)

gl = ax.gridlines(draw_labels=True, linewidth=0.4, color='gray', alpha=0.5)
gl.top_labels = False
gl.right_labels = False

cbar = plt.colorbar(im, ax=ax, shrink=0.7, pad=0.02, label='SST (°C)')

ax.set_title(f"Sea Surface Temperature — {str(sst_slice.time.values)[:10]}")
plt.savefig('sst_map.png', dpi=300, bbox_inches='tight')
plt.close(fig)
```

## SST Anomaly Map

Anomalies are diverging around zero. Use a diverging colormap centered on 0 by
setting symmetric `vmin`/`vmax`.

```python
fig = plt.figure(figsize=(12, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

anom = ds['sst_anomaly'].isel(time=-1)
vmax = 3.0   # symmetric limit in °C

im = ax.pcolormesh(
    ds.longitude, ds.latitude, anom,
    transform=ccrs.PlateCarree(),
    cmap='RdBu_r', vmin=-vmax, vmax=vmax,
    shading='auto',
)

ax.set_extent([-90, -80, 20, 30], crs=ccrs.PlateCarree())
ax.add_feature(cfeature.LAND, facecolor='lightgray', zorder=2)
ax.coastlines(resolution='10m', linewidth=0.6, zorder=3)

gl = ax.gridlines(draw_labels=True, linewidth=0.4, color='gray', alpha=0.5)
gl.top_labels = False
gl.right_labels = False

cbar = plt.colorbar(im, ax=ax, shrink=0.7, pad=0.02,
                    label='SST anomaly (°C)', extend='both')

ax.set_title('Sea Surface Temperature Anomaly')
plt.savefig('sst_anomaly_map.png', dpi=300, bbox_inches='tight')
plt.close(fig)
```

## DHW Bleaching-Alert Map

DHW is best shown with a discrete colormap keyed to the Coral Reef Watch alert
breakpoints, using `BoundaryNorm` so each band maps to a fixed color.

```python
from matplotlib.colors import ListedColormap, BoundaryNorm

# Breakpoints in °C-weeks and one color per interval
dhw_bounds = [0, 1, 4, 8, 12, 20]
dhw_colors = ['#FFFFCC', '#FFE066', '#FFA500', '#FF0000', '#8B0000']
dhw_cmap = ListedColormap(dhw_colors)
dhw_norm = BoundaryNorm(dhw_bounds, dhw_cmap.N)

fig = plt.figure(figsize=(12, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

dhw_slice = ds['dhw'].isel(time=-1)

im = ax.pcolormesh(
    ds.longitude, ds.latitude, dhw_slice,
    transform=ccrs.PlateCarree(),
    cmap=dhw_cmap, norm=dhw_norm,
    shading='auto',
)

ax.set_extent([-90, -80, 20, 30], crs=ccrs.PlateCarree())
ax.add_feature(cfeature.LAND, facecolor='lightgray', zorder=2)
ax.coastlines(resolution='10m', linewidth=0.6, zorder=3)

gl = ax.gridlines(draw_labels=True, linewidth=0.4, color='gray', alpha=0.5)
gl.top_labels = False
gl.right_labels = False

cbar = plt.colorbar(im, ax=ax, shrink=0.7, pad=0.02, ticks=dhw_bounds,
                    label='DHW (°C-weeks)', extend='max')

ax.set_title('Degree Heating Weeks — Coral Bleaching Alert')
plt.savefig('dhw_alert_map.png', dpi=300, bbox_inches='tight')
plt.close(fig)
```

## Styling Guidance

| Element        | Recommendation                                                        |
|----------------|-----------------------------------------------------------------------|
| Projection     | `PlateCarree` for regional lon/lat; `Mercator` for web-style basemaps |
| SST colormap   | `RdYlBu_r` or `cmocean.cm.thermal` (sequential warm)                  |
| Anomaly cmap   | `RdBu_r`, centered on 0 with symmetric `vmin`/`vmax`                   |
| DHW cmap       | Discrete `ListedColormap` + `BoundaryNorm` at CRW breakpoints         |
| Coastlines     | `'10m'` for regional maps; `'50m'`/`'110m'` for basin/global scale    |
| Land masking   | `cfeature.LAND` with high `zorder` so data does not bleed over land   |
| Gridlines      | Hide `top_labels`/`right_labels`; keep thin and semi-transparent      |
| Colorbar       | `shrink≈0.7`, `pad=0.02`; use `extend` when data exceeds limits       |

Notes:
- `transform=ccrs.PlateCarree()` always describes the **data** CRS (lon/lat),
  independent of the axes projection. Keep it on `pcolormesh` even when the axes
  use another projection.
- `set_extent` takes `[lon_min, lon_max, lat_min, lat_max]` and a `crs=`. Always
  pass `crs=ccrs.PlateCarree()` for geographic bounds.
- `cmocean` (`pip install cmocean`) provides oceanographic colormaps
  (`thermal`, `balance`, `haline`) but is optional; the matplotlib defaults
  above need no extra dependency.

## Export Settings

```python
# Publication raster
plt.savefig('map.png', dpi=300, bbox_inches='tight', facecolor='white')

# Vector output for figures/print
plt.savefig('map.pdf', bbox_inches='tight')   # or .svg

# Always release the figure in batch/loop contexts
plt.close('all')
```

- Use `dpi=300` for publication PNGs; `bbox_inches='tight'` trims whitespace.
- Set `facecolor='white'` so transparent backgrounds do not render black in
  some viewers.
- Prefer PDF/SVG when the figure will be scaled or embedded in a document.
- In loops, call `plt.close(fig)` after each save to avoid memory growth.

## See Also

- `SKILL.md` — map snippets in the Core Workflow.
- `references/thermal_stress.md` — DHW alert-level definitions.
