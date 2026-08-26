---
name: ltem-temporal-trends
domain: [fisheries-ecology]
data-source: [LTEM]
output-type: [analysis]
tags: [time-series, trend-detection, regime-shift, change-point]
peer_reviewed: true
status: stable
version: 0.2.0
description: This skill analyzes temporal trends in fish populations using the 26-year Baja California LTEM dataset (1998-2024). It provides workflows for time series analysis, trend detection, seasonal patterns, and change point detection. Use this skill when examining long-term changes in fish communities, detecting recovery patterns, or identifying regime shifts.
---

# LTEM Temporal Trends Analysis

## Purpose

This skill guides temporal analysis of fish populations using the Baja California LTEM dataset spanning 26 years (1998-2024). It helps marine scientists:
- Analyze long-term trends in fish biomass and abundance
- Detect change points and regime shifts
- Examine seasonal patterns in fish communities
- Compare temporal trajectories across regions
- Forecast future population trends
- Identify climate-driven changes

## Dataset Reference

**File:** `data/ltem_Ai2_v1.csv`
**Metadata:** `data/ltem_Ai2_v1_metadata.json`

> Paths shown are relative to your working directory; place your local copy of the LTEM dataset under `data/` (or adjust the paths) before running.

### Temporal Variables
| Column | Description |
|--------|-------------|
| `year` | Survey year (1998-2024) |
| `month` | Survey month (2-12) |
| `day` | Survey day |
| `mean_sst` | Annual mean SST |
| `mean_chl` | Annual mean Chlorophyll-a |

## Sampling Design & Aggregation Rules

**CRITICAL:** The LTEM dataset has a hierarchical sampling design. Proper aggregation is essential for valid time series analysis.

### Sampling Hierarchy
```
Region → Reef → Year → Depth → Transect → Species → Size class
```

The **transect** is the independent sampling unit. Each reef-year-depth combination typically has multiple replicate transects.

### Aggregation Rules for Temporal Analysis

**Rule 1: Always SUM biomass/quantity first at the transect level, THEN average across time periods.**

For annual time series:
```python
# Step 1: SUM biomass/quantity within each transect
transect_totals = df.groupby(['year', 'region', 'reef', 'depth', 'transect']).agg({
    'biomass': 'sum',
    'quantity': 'sum'
}).reset_index()

# Step 2: AVERAGE across transects for each year
annual_means = transect_totals.groupby('year').agg({
    'biomass': ['mean', 'std'],
    'quantity': ['mean', 'std']
})

# Count replicates (transects) per year for confidence intervals
n_per_year = transect_totals.groupby('year')['transect'].count()
```

For species-specific temporal trends:
```python
# Step 1: SUM within each transect FOR EACH SPECIES
transect_species = df.groupby(['year', 'region', 'reef', 'depth', 'transect', 'species']).agg({
    'biomass': 'sum',
    'quantity': 'sum'
}).reset_index()

# Step 2: AVERAGE by year and species
species_trends = transect_species.groupby(['year', 'species']).agg({
    'biomass': 'mean',
    'quantity': 'mean'
})
```

### Aggregation Rules for Size Time Series

**Rule 2: Size can be averaged directly without prior summation.**

```python
# Annual mean size (weighted by quantity recommended)
def weighted_mean_size(group):
    return np.average(group['size'], weights=group['quantity'])

annual_size = df.groupby('year').apply(weighted_mean_size)
```

### Quick Reference for Temporal Analysis

| Variable | Aggregation Method |
|----------|-------------------|
| `biomass` | SUM within transect → MEAN across transects per year |
| `quantity` | SUM within transect → MEAN across transects per year |
| `size` | MEAN directly per year (weight by quantity) |
| `species_richness` | COUNT DISTINCT species per transect → MEAN per year |
| Trend analysis n | Number of years (NOT transects or rows) |

### Special Considerations for Time Series

| Consideration | Approach |
|---------------|----------|
| Unequal sampling effort | Standardize by area or use mean per transect |
| Missing years | Note gaps; use interpolation cautiously |
| Varying reef coverage | Use consistent reef subset or account in model |
| Seasonal effects | Aggregate to annual or include month as covariate |

## Core Workflow

### 1. Load and Prepare Time Series Data

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.signal import savgol_filter

# Load LTEM data
ltem = pd.read_csv('data/ltem_Ai2_v1.csv')

# Create date column
ltem['date'] = pd.to_datetime(ltem[['year', 'month', 'day']])

print(f"Time range: {ltem['date'].min().date()} to {ltem['date'].max().date()}")
print(f"Years covered: {ltem['year'].nunique()}")
print(f"Surveys per year:
{ltem.groupby('year')['reef'].nunique()}")
```

### 2. Aggregate Annual Time Series

```python
def create_annual_time_series(df, group_cols=['year']):
    """
    Create annual time series of key metrics.
    """
    # Aggregate to annual level
    annual = df.groupby(group_cols).agg({
        'biomass': 'sum',
        'quantity': 'sum',
        'species': 'nunique',
        'reef': 'nunique',
        'mean_sst': 'mean',
        'mean_chl': 'mean',
        'transect': 'count'  # Number of observations
    }).reset_index()

    annual.columns = group_cols + ['total_biomass', 'total_abundance',
                                    'species_richness', 'n_reefs',
                                    'mean_sst', 'mean_chl', 'n_observations']

    # Calculate per-survey metrics (standardized)
    annual['biomass_per_reef'] = annual['total_biomass'] / annual['n_reefs']
    annual['abundance_per_reef'] = annual['total_abundance'] / annual['n_reefs']

    return annual

# Overall annual time series
annual_ts = create_annual_time_series(ltem)

# By region
annual_by_region = create_annual_time_series(ltem, ['year', 'region'])

print("Annual Time Series Summary:")
print(annual_ts.head(10))
```

### 3. Trend Analysis

```python
def analyze_trend(time_series, value_col, time_col='year'):
    """
    Analyze linear trend in time series.

    Returns:
        slope, intercept, r_value, p_value, std_err
        Mann-Kendall test results
        Sen's slope estimate
    """
    y = time_series[value_col].values
    x = time_series[time_col].values

    # Remove NaN
    mask = ~np.isnan(y)
    y = y[mask]
    x = x[mask]

    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    # Mann-Kendall trend test
    def mann_kendall(data):
        n = len(data)
        s = 0
        for i in range(n-1):
            for j in range(i+1, n):
                diff = data[j] - data[i]
                if diff > 0:
                    s += 1
                elif diff < 0:
                    s -= 1

        # Variance
        var_s = n * (n - 1) * (2 * n + 5) / 18

        # Z-score
        if s > 0:
            z = (s - 1) / np.sqrt(var_s)
        elif s < 0:
            z = (s + 1) / np.sqrt(var_s)
        else:
            z = 0

        p_mk = 2 * (1 - stats.norm.cdf(abs(z)))

        return s, z, p_mk

    s, z, p_mk = mann_kendall(y)

    # Sen's slope
    def sens_slope(data, times):
        n = len(data)
        slopes = []
        for i in range(n-1):
            for j in range(i+1, n):
                slopes.append((data[j] - data[i]) / (times[j] - times[i]))
        return np.median(slopes)

    sen_slope = sens_slope(y, x)

    print(f"
Trend Analysis for {value_col}:")
    print(f"  Linear regression: slope={slope:.4f}/year, R²={r_value**2:.3f}, p={p_value:.4f}")
    print(f"  Mann-Kendall: S={s}, Z={z:.2f}, p={p_mk:.4f}")
    print(f"  Sen's slope: {sen_slope:.4f}/year")
    print(f"  Total change over period: {sen_slope * (x.max() - x.min()):.2f}")

    return {
        'linear_slope': slope,
        'r_squared': r_value**2,
        'linear_p': p_value,
        'mk_statistic': s,
        'mk_z': z,
        'mk_p': p_mk,
        'sens_slope': sen_slope
    }

# Analyze trends
biomass_trend = analyze_trend(annual_ts, 'biomass_per_reef')
richness_trend = analyze_trend(annual_ts, 'species_richness')
```

### 4. Regional Trend Comparison

```python
def compare_regional_trends(df):
    """
    Compare temporal trends across regions.
    """
    regions = df['region'].unique()
    trend_results = []

    for region in regions:
        region_data = df[df['region'] == region]
        if len(region_data) < 5:  # Skip regions with insufficient data
            continue

        # Linear regression on biomass
        x = region_data['year'].values
        y = region_data['biomass_per_reef'].values

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        trend_results.append({
            'region': region,
            'slope': slope,
            'r_squared': r_value**2,
            'p_value': p_value,
            'trend': 'Increasing' if slope > 0 and p_value < 0.05 else
                     'Decreasing' if slope < 0 and p_value < 0.05 else 'Stable',
            'n_years': len(region_data)
        })

    results_df = pd.DataFrame(trend_results)
    print("
Regional Trend Comparison:")
    print(results_df.sort_values('slope', ascending=False))

    return results_df

regional_trends = compare_regional_trends(annual_by_region)
```

### 5. Change Point Detection

```python
def detect_change_points(time_series, value_col, method='pettitt'):
    """
    Detect change points in time series.

    Methods:
    - pettitt: Pettitt test for single change point
    - cusum: CUSUM method for cumulative deviations
    """
    y = time_series[value_col].values
    years = time_series['year'].values
    n = len(y)

    if method == 'pettitt':
        # Pettitt test
        U = np.zeros(n)
        for t in range(n):
            for i in range(t):
                for j in range(t, n):
                    U[t] += np.sign(y[j] - y[i])

        K = np.max(np.abs(U))
        t_change = np.argmax(np.abs(U))
        change_year = years[t_change]

        # P-value approximation
        p_value = 2 * np.exp(-6 * K**2 / (n**3 + n**2))

        print(f"
Pettitt Test for {value_col}:")
        print(f"  Change point detected: {change_year}")
        print(f"  Test statistic K: {K:.0f}")
        print(f"  P-value: {p_value:.4f}")
        print(f"  Significant (p<0.05): {p_value < 0.05}")

        # Calculate means before/after
        before_mean = y[:t_change].mean()
        after_mean = y[t_change:].mean()
        print(f"  Mean before {change_year}: {before_mean:.2f}")
        print(f"  Mean after {change_year}: {after_mean:.2f}")

        return change_year, p_value, t_change

    elif method == 'cusum':
        # CUSUM method
        mean_y = y.mean()
        cusum = np.cumsum(y - mean_y)
        cusum_range = cusum.max() - cusum.min()

        # Bootstrap confidence interval
        n_bootstrap = 1000
        bootstrap_ranges = []
        for _ in range(n_bootstrap):
            shuffled = np.random.permutation(y)
            boot_cusum = np.cumsum(shuffled - mean_y)
            bootstrap_ranges.append(boot_cusum.max() - boot_cusum.min())

        ci_95 = np.percentile(bootstrap_ranges, 95)
        significant = cusum_range > ci_95

        # Find change point
        t_change = np.argmax(np.abs(cusum))
        change_year = years[t_change]

        print(f"
CUSUM Analysis for {value_col}:")
        print(f"  Change point: {change_year}")
        print(f"  CUSUM range: {cusum_range:.2f}")
        print(f"  95% CI threshold: {ci_95:.2f}")
        print(f"  Significant: {significant}")

        return change_year, significant, cusum

# Detect change points
cp_biomass = detect_change_points(annual_ts, 'biomass_per_reef', 'pettitt')
cp_richness = detect_change_points(annual_ts, 'species_richness', 'pettitt')
```

### 6. Seasonal Patterns

```python
def analyze_seasonal_patterns(df):
    """
    Analyze seasonal patterns in sampling and fish metrics.
    """
    # Monthly aggregation
    monthly = df.groupby('month').agg({
        'biomass': ['mean', 'std'],
        'quantity': ['mean', 'std'],
        'species': 'nunique',
        'transect': 'count'
    })
    monthly.columns = ['biomass_mean', 'biomass_std',
                       'abundance_mean', 'abundance_std',
                       'species_richness', 'n_observations']
    monthly = monthly.reset_index()

    print("
Seasonal Patterns (by Month):")
    print(monthly)

    # Peak month
    peak_biomass = monthly.loc[monthly['biomass_mean'].idxmax(), 'month']
    print(f"
Peak biomass month: {peak_biomass}")

    return monthly

seasonal = analyze_seasonal_patterns(ltem)
```

### 7. Moving Window Analysis

```python
def moving_window_analysis(time_series, value_col, window=5):
    """
    Calculate moving averages and detect periods of change.
    """
    ts = time_series.copy()

    # Moving average
    ts['ma'] = ts[value_col].rolling(window=window, center=True).mean()
    ts['ma_std'] = ts[value_col].rolling(window=window, center=True).std()

    # Rate of change (year-over-year)
    ts['pct_change'] = ts[value_col].pct_change() * 100

    # Smoothed trend (Savitzky-Golay filter)
    if len(ts) >= 7:
        ts['smoothed'] = savgol_filter(ts[value_col].fillna(method='ffill'),
                                        window_length=7, polyorder=2)

    # Identify acceleration/deceleration periods
    ts['trend_direction'] = np.where(ts['pct_change'] > 5, 'Increasing',
                                      np.where(ts['pct_change'] < -5, 'Decreasing',
                                               'Stable'))

    return ts

smoothed_ts = moving_window_analysis(annual_ts, 'biomass_per_reef', window=5)
print("
Moving Window Analysis:")
print(smoothed_ts[['year', 'biomass_per_reef', 'ma', 'pct_change', 'trend_direction']].tail(10))
```

### 8. Create Temporal Visualizations

```python
# Set theme
ocean_colors = ['#023E8A', '#0077B6', '#00B4D8', '#48CAE4', '#90E0EF', '#CAF0F8', '#00ABC8']
fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# 1. Overall biomass time series with trend
ax1 = axes[0, 0]
ax1.plot(annual_ts['year'], annual_ts['biomass_per_reef'], 'o-',
         color='#0077B6', label='Observed')

# Add trend line
x = annual_ts['year'].values
y = annual_ts['biomass_per_reef'].values
z = np.polyfit(x, y, 1)
p = np.poly1d(z)
ax1.plot(x, p(x), '--', color='red', alpha=0.7,
         label=f'Trend: {z[0]:.3f}/year')

# Smoothed line
if 'smoothed' in smoothed_ts.columns:
    ax1.plot(smoothed_ts['year'], smoothed_ts['smoothed'],
             color='green', alpha=0.5, label='Smoothed')

ax1.set_xlabel('Year')
ax1.set_ylabel('Biomass per Reef (ton/ha)')
ax1.set_title('Fish Biomass Time Series (1998-2024)')
ax1.legend()

# 2. Regional trends comparison
ax2 = axes[0, 1]
for i, region in enumerate(annual_by_region['region'].unique()):
    region_data = annual_by_region[annual_by_region['region'] == region]
    ax2.plot(region_data['year'], region_data['biomass_per_reef'],
             'o-', label=region, color=ocean_colors[i % len(ocean_colors)], alpha=0.7)

ax2.set_xlabel('Year')
ax2.set_ylabel('Biomass per Reef (ton/ha)')
ax2.set_title('Regional Biomass Trends')
ax2.legend(fontsize=8)

# 3. Species richness trend
ax3 = axes[1, 0]
ax3.fill_between(annual_ts['year'], 0, annual_ts['species_richness'],
                  alpha=0.3, color='#0077B6')
ax3.plot(annual_ts['year'], annual_ts['species_richness'], 'o-',
         color='#023E8A')
ax3.set_xlabel('Year')
ax3.set_ylabel('Species Richness')
ax3.set_title('Species Richness Over Time')

# 4. Change point visualization (CUSUM)
ax4 = axes[1, 1]
y = annual_ts['biomass_per_reef'].values
mean_y = y.mean()
cusum = np.cumsum(y - mean_y)
ax4.plot(annual_ts['year'], cusum, 'o-', color='#0077B6')
ax4.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
ax4.fill_between(annual_ts['year'], 0, cusum,
                  where=(cusum > 0), alpha=0.3, color='green', label='Above mean')
ax4.fill_between(annual_ts['year'], 0, cusum,
                  where=(cusum < 0), alpha=0.3, color='red', label='Below mean')

# Mark change point
if cp_biomass[0]:
    ax4.axvline(x=cp_biomass[0], color='red', linestyle='--',
                label=f'Change point: {cp_biomass[0]}')

ax4.set_xlabel('Year')
ax4.set_ylabel('Cumulative Sum')
ax4.set_title('CUSUM Change Point Analysis')
ax4.legend()

plt.tight_layout()
plt.savefig('ltem_temporal_trends.png', dpi=300, bbox_inches='tight')
plt.show()
```

### 9. Generate Temporal Report

Use the `LTEMReportGenerator` class to create comprehensive, publication-quality temporal analysis reports following the CBMC format.

```python
# Import report generator
from chatmpa.report import (
    LTEMReportGenerator,
    generate_environmental_context,
    generate_conclusion_section,
)

# Key statistics
start_year = annual_ts['year'].min()
end_year = annual_ts['year'].max()
total_years = end_year - start_year + 1

# Overall trend
trend_direction = 'creciente' if biomass_trend['linear_slope'] > 0 else 'decreciente'
trend_sig = 'significativa' if biomass_trend['linear_p'] < 0.05 else 'no significativa'

# Create comprehensive LTEM temporal report
report = LTEMReportGenerator(
    title="Análisis de Tendencias Temporales",
    region="Golfo de California",
    period=f"{start_year}-{end_year}",
    language="es"  # or "en" for English
)

# Add authors
report.add_author("Fabio Favoretto", "Ph.D.", "CBMC", "author")

# Add time series overview as introduction
overview = f"""Este informe presenta el análisis de tendencias temporales de las comunidades de peces
utilizando {total_years} años de datos del programa LTEM (Long-Term Ecological Monitoring)
en Baja California.

### Resumen de la serie temporal

| Parámetro | Valor |
|-----------|-------|
| Año inicial | {start_year} |
| Año final | {end_year} |
| Total de años | {total_years} |
| Puntos de datos | {len(annual_ts)} |
| Promedio de arrecifes por año | {annual_ts['n_reefs'].mean():.0f} |
"""
report.add_section("Resumen temporal", overview, "introduction")

# Add trend analysis section
trend_section = f"""### Tendencia general de biomasa

- **Dirección:** {trend_direction.capitalize()}
- **Significancia estadística:** {trend_sig} (p = {biomass_trend['linear_p']:.4f})
- **Pendiente lineal:** {biomass_trend['linear_slope']:.4f} ton/ha por año
- **Pendiente de Sen:** {biomass_trend['sens_slope']:.4f} ton/ha por año
- **R²:** {biomass_trend['r_squared']:.3f}

### Prueba de Mann-Kendall

| Estadístico | Valor |
|-------------|-------|
| S | {biomass_trend['mk_statistic']} |
| Z | {biomass_trend['mk_z']:.2f} |
| p-valor | {biomass_trend['mk_p']:.4f} |

La prueba de Mann-Kendall es un test no paramétrico robusto para detectar tendencias
monotónicas en series temporales, particularmente útil para datos ecológicos.
"""
report.add_section("Análisis de tendencias", trend_section, "results")

# Add change point detection section
change_point_year = cp_biomass[0]
change_point_p = cp_biomass[1]
change_significant = change_point_p < 0.05

changepoint_section = f"""### Detección de puntos de cambio (Test de Pettitt)

| Parámetro | Valor |
|-----------|-------|
| Año de cambio detectado | {change_point_year} |
| p-valor | {change_point_p:.4f} |
| Interpretación | {'Cambio significativo detectado' if change_significant else 'Sin cambio significativo'} |

{'El análisis identifica un cambio de régimen potencial alrededor de ' + str(change_point_year) + ', lo cual podría estar relacionado con eventos climáticos como El Niño o cambios en las presiones de pesca.' if change_significant else 'No se detectaron cambios de régimen significativos en la serie temporal.'}

### Análisis CUSUM

El gráfico CUSUM (suma acumulativa) visualiza las desviaciones acumuladas respecto a la media,
permitiendo identificar períodos de biomasa consistentemente alta o baja.
"""
report.add_section("Puntos de cambio", changepoint_section, "results")

# Add regional trends section
n_increasing = len(regional_trends[regional_trends['trend'] == 'Increasing'])
n_decreasing = len(regional_trends[regional_trends['trend'] == 'Decreasing'])
n_stable = len(regional_trends[regional_trends['trend'] == 'Stable'])

regional_section = f"""### Comparación de tendencias regionales

{regional_trends.to_markdown(index=False)}

**Resumen:**
- Regiones con tendencia creciente: {n_increasing}
- Regiones con tendencia decreciente: {n_decreasing}
- Regiones estables: {n_stable}

La variación regional en las tendencias temporales refleja diferencias en las condiciones
ambientales locales, presión pesquera y nivel de protección.
"""
report.add_section("Tendencias regionales", regional_section, "results")

# Add figures
report.add_figure('ltem_temporal_trends.png',
                  'Análisis de tendencias temporales incluyendo serie de biomasa, comparación regional, riqueza de especies y análisis CUSUM')

# Add conclusion
conclusion = generate_conclusion_section(
    key_findings=[
        f"La biomasa de peces muestra una tendencia {trend_direction} durante {total_years} años de monitoreo",
        f"La pendiente de Sen indica un cambio de {biomass_trend['sens_slope']:.4f} ton/ha por año",
        f"{'Se detectó un cambio de régimen significativo alrededor de ' + str(change_point_year) if change_significant else 'No se detectaron cambios de régimen significativos'}",
        f"{n_increasing} regiones muestran tendencias crecientes, {n_decreasing} decrecientes y {n_stable} estables",
        f"El monitoreo incluye un promedio de {annual_ts['n_reefs'].mean():.0f} arrecifes por año"
    ],
    recommendations=[
        "Continuar el monitoreo a largo plazo para seguir las tendencias actuales",
        "Investigar los factores que impulsan los puntos de cambio detectados",
        "Enfocar esfuerzos de conservación en regiones con tendencias decrecientes",
        "Correlacionar tendencias con variables climáticas (SST, ENSO)",
        "Evaluar el impacto de las áreas marinas protegidas en las tendencias temporales"
    ]
)
report.add_section("Conclusión", conclusion, "conclusion")

# Add key references
report.add_reference("Bond, N. A., et al. (2015). Causes and impacts of the 2014 warm anomaly in the NE Pacific. Geophysical Research Letters, 42(9), 3414-3420.")
report.add_reference("Frölicher, T. L., et al. (2018). Marine heatwaves under global warming. Nature, 560(7718), 360-364.")
report.add_reference("Favoretto, F., et al. (2024). Trophic restructuring and warming-driven tropicalization in Gulf of California rocky reefs. Global Change Biology.")

# Export Markdown + HTML + PDF in one call
paths = report.export_all(
    output_dir="output/",           # folder for all output files
    base_name="ltem_temporal_report",
    figures_dir="output/figures",   # where figures are saved
)
# paths = {'md': '...md', 'html': '...html', 'pdf': '...pdf' or None}
print("Reports generated:", paths)
```

## References

- **`../ltem-fish-community/references/report_template.py`** - CBMC-format report generator module with `LTEMReportGenerator` class
- **`references/time_series_methods.md`** - Statistical methods for ecological time series
- **`references/change_point_detection.md`** - Change point detection algorithms
- **`references/regime_shifts.md`** - Marine ecosystem regime shifts

## Success Criteria

A successful temporal trends analysis includes:
- [ ] Annual time series constructed
- [ ] Linear trend analysis completed
- [ ] Mann-Kendall test performed
- [ ] Change points detected
- [ ] Regional trends compared
- [ ] At least 4 time series visualizations
- [ ] Temporal report generated
- [ ] Key trends and shifts documented
