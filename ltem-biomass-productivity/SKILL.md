---
name: ltem-biomass-productivity
domain: [fisheries-ecology]
data-source: [LTEM]
output-type: [analysis]
tags: [biomass, productivity, turnover, environmental-drivers, sst, chlorophyll]
status: stable
version: 0.2.0
description: This skill analyzes fish biomass, productivity, turnover rates, and environmental drivers using the Baja California LTEM dataset. It provides workflows for calculating biomass metrics, analyzing productivity patterns, examining SST and chlorophyll relationships, and identifying environmental drivers of fish community structure. Use this skill for production ecology questions, environmental correlation analysis, or climate-fish relationships.
---

# LTEM Biomass, Productivity & Environmental Analysis

## Purpose

This skill guides the analysis of fish production ecology and environmental relationships using the Baja California LTEM dataset. It helps marine scientists:
- Analyze fish biomass and density patterns
- Calculate and interpret productivity metrics
- Examine biomass turnover rates
- Correlate fish metrics with SST and chlorophyll-a
- Identify environmental drivers of community structure
- Model climate-fish relationships

## Dataset Reference

**File:** `data/ltem_Ai2_v1.csv`
**Metadata:** `data/ltem_Ai2_v1_metadata.json`

> Paths shown are relative to your working directory; place your local copy of the LTEM dataset under `data/` (or adjust the paths) before running.

### Biomass & Productivity Variables
| Column | Description | Units |
|--------|-------------|-------|
| `biomass` | Fish biomass | ton/ha |
| `prod` | Estimated productivity | - |
| `turnover` | Biomass turnover rate | - |
| `quantity` | Number of individuals | count |
| `size` | Fish total length | cm |

### Environmental Variables
| Column | Description | Units |
|--------|-------------|-------|
| `mean_sst` | Annual mean SST | °C |
| `mean_chl` | Annual mean Chlorophyll-a | mg/m³ |

## Sampling Design & Aggregation Rules

**CRITICAL:** The LTEM dataset has a hierarchical sampling design. Proper aggregation is essential for valid biomass and environmental correlation analyses.

### Sampling Hierarchy
```
Region → Reef → Year → Depth → Transect → Species → Size class
```

The **transect** is the independent sampling unit. Each reef-year-depth combination typically has multiple replicate transects.

### Aggregation Rules for Biomass Analysis

**Rule 1: Always SUM biomass/quantity first at the transect level, THEN average across your grouping factor.**

For regional/spatial comparisons:
```python
# Step 1: SUM biomass/quantity within each transect
transect_totals = df.groupby(['year', 'region', 'reef', 'depth', 'transect']).agg({
    'biomass': 'sum',
    'quantity': 'sum',
    'prod': 'sum',  # Productivity also needs summing
    'mean_sst': 'first',  # Environmental vars are the same within transect
    'mean_chl': 'first'
}).reset_index()

# Step 2: AVERAGE across transects for regional comparison
regional_biomass = transect_totals.groupby('region').agg({
    'biomass': ['mean', 'std'],
    'quantity': ['mean', 'std'],
    'prod': 'mean'
})
```

For trophic group analysis:
```python
# Step 1: SUM within each transect FOR EACH TROPHIC GROUP
transect_trophic = df.groupby(['year', 'region', 'reef', 'depth', 'transect',
                                'trophic_group']).agg({
    'biomass': 'sum',
    'quantity': 'sum',
    'prod': 'sum'
}).reset_index()

# Step 2: AVERAGE by trophic group
trophic_means = transect_trophic.groupby('trophic_group').agg({
    'biomass': 'mean',
    'quantity': 'mean',
    'prod': 'mean'
})
```

### Aggregation Rules for Environmental Correlations

**Rule 3: Correlate transect-level biomass totals with environmental variables.**

```python
# Correct: Use transect-level biomass for correlations
transect_totals = df.groupby(['year', 'region', 'reef', 'depth', 'transect']).agg({
    'biomass': 'sum',
    'mean_sst': 'first',
    'mean_chl': 'first'
}).reset_index()

# Correlation using transect as sampling unit
rho, p = stats.spearmanr(transect_totals['mean_sst'], transect_totals['biomass'])
```

### Aggregation Rules for Size and Turnover

**Rule 2: Size and turnover can be averaged directly (turnover is a rate).**

```python
# Size: weighted mean by quantity
def weighted_mean_size(group):
    return np.average(group['size'], weights=group['quantity'])

# Turnover: mean (it's already a rate, biomass-weighted if needed)
def weighted_mean_turnover(group):
    return np.average(group['turnover'], weights=group['biomass'])

regional_size = df.groupby('region').apply(weighted_mean_size)
regional_turnover = df.groupby('region').apply(weighted_mean_turnover)
```

### Quick Reference for Biomass/Productivity Analysis

| Variable | Aggregation Method |
|----------|-------------------|
| `biomass` | SUM within transect → MEAN across transects |
| `quantity` | SUM within transect → MEAN across transects |
| `prod` | SUM within transect → MEAN across transects |
| `turnover` | MEAN (weighted by biomass) |
| `size` | MEAN (weighted by quantity) |
| `mean_sst`, `mean_chl` | Already at appropriate level; use with transect totals |
| Correlation n | Number of transects (NOT raw rows) |

### Common Mistakes in Biomass/Environmental Analysis

| Mistake | Problem | Correct Approach |
|---------|---------|------------------|
| Correlating row-level biomass with SST | Pseudoreplication, inflated r² | Sum biomass at transect first |
| Averaging biomass across species | Loses total biomass information | Sum species within transect |
| Comparing productivity directly | Productivity must be summed like biomass | Sum prod at transect level |
| Weighting turnover by quantity | Turnover relates to biomass, not abundance | Weight by biomass instead |

## Core Workflow

### 1. Load and Explore Biomass Data

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor

# Load LTEM data
ltem = pd.read_csv('data/ltem_Ai2_v1.csv')

# Basic biomass statistics
print("Biomass Statistics:")
print(ltem['biomass'].describe())
print(f"\nTotal biomass in dataset: {ltem['biomass'].sum():.2f} ton/ha")
print(f"Mean biomass per observation: {ltem['biomass'].mean():.4f} ton/ha")

# Environmental range
print(f"\nSST range: {ltem['mean_sst'].min():.1f} - {ltem['mean_sst'].max():.1f} °C")
print(f"Chl-a range: {ltem['mean_chl'].min():.2f} - {ltem['mean_chl'].max():.2f} mg/m³")
```

### 2. Aggregate Biomass to Survey Level

```python
def aggregate_biomass(df):
    """
    Aggregate biomass metrics to survey level.
    """
    # Create survey identifier
    df['survey_id'] = (df['reef'] + '_' + df['year'].astype(str) + '_' + df['depth'])

    # Aggregate
    survey_data = df.groupby(['survey_id', 'region', 'reef', 'year', 'depth',
                              'latitude', 'longitude', 'mean_sst', 'mean_chl']).agg({
        'biomass': 'sum',
        'prod': 'sum',
        'turnover': 'mean',
        'quantity': 'sum',
        'size': 'mean',
        'area': 'sum',
        'species': 'nunique',
        'trophic_level': 'mean',
        'transect': 'nunique'
    }).reset_index()

    survey_data.columns = ['survey_id', 'region', 'reef', 'year', 'depth',
                           'latitude', 'longitude', 'mean_sst', 'mean_chl',
                           'total_biomass', 'total_prod', 'mean_turnover',
                           'total_abundance', 'mean_size', 'total_area',
                           'species_richness', 'mean_trophic_level', 'n_transects']

    # Calculate densities (per 100 m²)
    survey_data['biomass_density'] = (survey_data['total_biomass'] /
                                       survey_data['total_area']) * 100
    survey_data['abundance_density'] = (survey_data['total_abundance'] /
                                         survey_data['total_area']) * 100
    survey_data['prod_density'] = (survey_data['total_prod'] /
                                    survey_data['total_area']) * 100

    return survey_data

surveys = aggregate_biomass(ltem)
print(f"\nTotal surveys: {len(surveys)}")
print(f"Mean survey biomass: {surveys['total_biomass'].mean():.2f} ton/ha")
```

### 3. Biomass Patterns by Region and Depth

```python
def analyze_biomass_patterns(df):
    """
    Analyze biomass patterns across spatial factors.
    """
    # By region
    region_biomass = df.groupby('region').agg({
        'total_biomass': ['mean', 'std', 'median'],
        'biomass_density': ['mean', 'std'],
        'mean_turnover': 'mean',
        'species_richness': 'mean'
    }).round(2)

    print("Biomass by Region:")
    print(region_biomass)

    # By depth
    depth_biomass = df.groupby('depth').agg({
        'total_biomass': ['mean', 'std', 'median'],
        'biomass_density': ['mean', 'std'],
        'total_prod': 'mean'
    }).round(2)

    print("\nBiomass by Depth:")
    print(depth_biomass)

    # Statistical test: Region effect
    groups = [group['total_biomass'].values
              for name, group in df.groupby('region')]
    stat, p_value = stats.kruskal(*groups)
    print(f"\nKruskal-Wallis (Region effect): H={stat:.2f}, p={p_value:.4e}")

    # Depth effect
    shallow = df[df['depth'] == 'Shallow']['total_biomass']
    deep = df[df['depth'] == 'Deep']['total_biomass']
    stat, p_value = stats.mannwhitneyu(shallow, deep)
    print(f"Mann-Whitney (Depth effect): U={stat:.0f}, p={p_value:.4e}")
    print(f"  Shallow mean: {shallow.mean():.2f}, Deep mean: {deep.mean():.2f}")

    return region_biomass, depth_biomass

region_stats, depth_stats = analyze_biomass_patterns(surveys)
```

### 4. Trophic-Specific Biomass

```python
def trophic_biomass_analysis(df):
    """
    Analyze biomass across trophic levels.
    """
    original_df = pd.read_csv('data/ltem_Ai2_v1.csv')

    # Define trophic groups
    def trophic_group(tl):
        if tl < 2.5: return 'Herbivores (TL<2.5)'
        elif tl < 3.0: return 'Low Omnivores (2.5-3.0)'
        elif tl < 3.5: return 'Omnivores (3.0-3.5)'
        elif tl < 4.0: return 'Carnivores (3.5-4.0)'
        else: return 'Top Predators (TL>4.0)'

    original_df['trophic_group'] = original_df['trophic_level'].apply(trophic_group)

    # Biomass by trophic group
    trophic_data = original_df.groupby('trophic_group').agg({
        'biomass': ['sum', 'mean'],
        'prod': 'sum',
        'turnover': 'mean',
        'quantity': 'sum',
        'species': 'nunique'
    }).round(3)

    trophic_data.columns = ['total_biomass', 'mean_biomass', 'total_prod',
                            'mean_turnover', 'total_abundance', 'n_species']

    # Calculate proportions
    trophic_data['biomass_proportion'] = (trophic_data['total_biomass'] /
                                           trophic_data['total_biomass'].sum() * 100)

    print("Biomass by Trophic Group:")
    print(trophic_data.sort_values('total_biomass', ascending=False).round(2))

    # Trophic efficiency
    print(f"\nMean Turnover by Trophic Group:")
    print(original_df.groupby('trophic_group')['turnover'].mean().round(3))

    return trophic_data

trophic_biomass = trophic_biomass_analysis(ltem)
```

### 5. Environmental Correlations

```python
def environmental_correlations(df):
    """
    Analyze correlations between fish metrics and environmental variables.
    """
    # Variables to correlate
    fish_vars = ['total_biomass', 'total_abundance', 'species_richness',
                 'mean_trophic_level', 'mean_size', 'total_prod', 'mean_turnover']
    env_vars = ['mean_sst', 'mean_chl']

    # Calculate Spearman correlations
    correlations = []
    for fish_var in fish_vars:
        for env_var in env_vars:
            # Remove NaN
            mask = ~(df[fish_var].isna() | df[env_var].isna())
            x = df.loc[mask, env_var]
            y = df.loc[mask, fish_var]

            if len(x) < 10:
                continue

            rho, p_value = stats.spearmanr(x, y)

            correlations.append({
                'fish_variable': fish_var,
                'env_variable': env_var,
                'spearman_rho': rho,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'n': len(x)
            })

    corr_df = pd.DataFrame(correlations)

    print("Environmental Correlations (Spearman):")
    print(corr_df.round(3))

    # Correlation matrix heatmap
    all_vars = fish_vars + env_vars
    corr_matrix = df[all_vars].corr(method='spearman')

    return corr_df, corr_matrix

env_corr, corr_matrix = environmental_correlations(surveys)
```

### 6. SST-Biomass Relationship

```python
def analyze_sst_biomass(df):
    """
    Detailed analysis of SST effects on fish biomass.
    """
    # Remove NaN
    clean_df = df.dropna(subset=['mean_sst', 'total_biomass'])

    # Bin SST for categorical analysis
    sst_bins = [21, 23, 24, 25, 26, 27]
    sst_labels = ['21-23°C', '23-24°C', '24-25°C', '25-26°C', '26-27°C']
    clean_df['sst_bin'] = pd.cut(clean_df['mean_sst'], bins=sst_bins, labels=sst_labels)

    # Biomass by SST bin
    sst_biomass = clean_df.groupby('sst_bin').agg({
        'total_biomass': ['mean', 'std', 'count'],
        'species_richness': 'mean',
        'mean_trophic_level': 'mean'
    }).round(2)

    print("Biomass by SST Range:")
    print(sst_biomass)

    # Linear regression
    X = clean_df['mean_sst'].values.reshape(-1, 1)
    y = clean_df['total_biomass'].values

    model = LinearRegression()
    model.fit(X, y)
    r_squared = model.score(X, y)

    print(f"\nLinear Model: Biomass = {model.coef_[0]:.3f} * SST + {model.intercept_:.3f}")
    print(f"R² = {r_squared:.3f}")

    # Check for non-linear relationship
    from scipy.optimize import curve_fit

    def quadratic(x, a, b, c):
        return a * x**2 + b * x + c

    try:
        popt, pcov = curve_fit(quadratic, clean_df['mean_sst'], clean_df['total_biomass'])
        y_pred = quadratic(clean_df['mean_sst'], *popt)
        ss_res = np.sum((clean_df['total_biomass'] - y_pred)**2)
        ss_tot = np.sum((clean_df['total_biomass'] - clean_df['total_biomass'].mean())**2)
        r2_quad = 1 - (ss_res / ss_tot)

        print(f"\nQuadratic Model: R² = {r2_quad:.3f}")
        if r2_quad > r_squared:
            print("  Non-linear relationship detected - quadratic fits better")
            optimal_sst = -popt[1] / (2 * popt[0])
            print(f"  Optimal SST: {optimal_sst:.1f}°C")
    except:
        pass

    return sst_biomass, model

sst_analysis, sst_model = analyze_sst_biomass(surveys)
```

### 7. Chlorophyll-Productivity Relationship

```python
def analyze_chl_productivity(df):
    """
    Analyze relationship between chlorophyll-a and fish productivity.
    """
    clean_df = df.dropna(subset=['mean_chl', 'total_prod', 'total_biomass'])

    # Bin Chl-a
    chl_bins = [0, 0.5, 1.0, 2.0, 4.0, 8.0]
    chl_labels = ['<0.5', '0.5-1', '1-2', '2-4', '>4']
    clean_df['chl_bin'] = pd.cut(clean_df['mean_chl'], bins=chl_bins, labels=chl_labels)

    # Productivity by Chl-a bin
    chl_prod = clean_df.groupby('chl_bin').agg({
        'total_prod': ['mean', 'std'],
        'total_biomass': 'mean',
        'mean_turnover': 'mean',
        'survey_id': 'count'
    }).round(3)

    print("Productivity by Chlorophyll Range:")
    print(chl_prod)

    # Correlation
    rho, p = stats.spearmanr(clean_df['mean_chl'], clean_df['total_prod'])
    print(f"\nChl-a vs Productivity: Spearman ρ = {rho:.3f}, p = {p:.4f}")

    # Log-log relationship (common in productivity studies)
    log_chl = np.log10(clean_df['mean_chl'] + 0.01)
    log_prod = np.log10(clean_df['total_prod'] + 0.01)

    slope, intercept, r, p, se = stats.linregress(log_chl, log_prod)
    print(f"\nLog-Log Model: log(Prod) = {slope:.3f} * log(Chl) + {intercept:.3f}")
    print(f"R² = {r**2:.3f}")

    return chl_prod

chl_analysis = analyze_chl_productivity(surveys)
```

### 8. Latitudinal Gradients

```python
def latitudinal_analysis(df):
    """
    Analyze latitudinal gradients in biomass and productivity.
    """
    # Bin by latitude degree
    df['lat_bin'] = np.floor(df['latitude']).astype(int)

    # Metrics by latitude
    lat_gradient = df.groupby('lat_bin').agg({
        'total_biomass': ['mean', 'std'],
        'species_richness': 'mean',
        'total_prod': 'mean',
        'mean_sst': 'mean',
        'mean_chl': 'mean',
        'survey_id': 'count'
    }).round(2)

    print("Latitudinal Gradient:")
    print(lat_gradient)

    # Correlation with latitude
    rho_bio, p_bio = stats.spearmanr(df['latitude'], df['total_biomass'])
    rho_rich, p_rich = stats.spearmanr(df['latitude'], df['species_richness'])

    print(f"\nLatitude correlations:")
    print(f"  Biomass: ρ = {rho_bio:.3f}, p = {p_bio:.4f}")
    print(f"  Richness: ρ = {rho_rich:.3f}, p = {p_rich:.4f}")

    return lat_gradient

lat_results = latitudinal_analysis(surveys)
```

### 9. Create Visualizations

```python
# Set theme
ocean_colors = ['#023E8A', '#0077B6', '#00B4D8', '#48CAE4', '#90E0EF', '#CAF0F8']
fig, axes = plt.subplots(2, 3, figsize=(16, 10))

# 1. Biomass by region
ax1 = axes[0, 0]
region_order = surveys.groupby('region')['total_biomass'].mean().sort_values().index
surveys.boxplot(column='total_biomass', by='region', ax=ax1)
ax1.set_xlabel('Region')
ax1.set_ylabel('Total Biomass (ton/ha)')
ax1.set_title('Biomass by Region')
plt.sca(ax1)
plt.suptitle('')
plt.xticks(rotation=45, ha='right')

# 2. SST vs Biomass scatter
ax2 = axes[0, 1]
scatter = ax2.scatter(surveys['mean_sst'], surveys['total_biomass'],
                      c=surveys['mean_chl'], cmap='YlGnBu', alpha=0.6, s=30)
ax2.set_xlabel('Mean SST (°C)')
ax2.set_ylabel('Total Biomass (ton/ha)')
ax2.set_title('Biomass vs SST (colored by Chl-a)')
plt.colorbar(scatter, ax=ax2, label='Chl-a (mg/m³)')

# Trend line
z = np.polyfit(surveys['mean_sst'].dropna(), surveys['total_biomass'].dropna(), 1)
p = np.poly1d(z)
x_line = np.linspace(surveys['mean_sst'].min(), surveys['mean_sst'].max(), 100)
ax2.plot(x_line, p(x_line), 'r--', alpha=0.7)

# 3. Chl-a vs Productivity
ax3 = axes[0, 2]
ax3.scatter(surveys['mean_chl'], surveys['total_prod'],
            color='#0077B6', alpha=0.5, s=30)
ax3.set_xlabel('Mean Chl-a (mg/m³)')
ax3.set_ylabel('Total Productivity')
ax3.set_title('Productivity vs Chlorophyll-a')
ax3.set_xscale('log')
ax3.set_yscale('log')

# 4. Correlation heatmap
ax4 = axes[1, 0]
vars_for_heatmap = ['total_biomass', 'species_richness', 'mean_trophic_level',
                    'mean_size', 'mean_sst', 'mean_chl']
corr_subset = surveys[vars_for_heatmap].corr(method='spearman')
sns.heatmap(corr_subset, annot=True, fmt='.2f', cmap='RdBu_r',
            center=0, ax=ax4, vmin=-1, vmax=1)
ax4.set_title('Spearman Correlations')

# 5. Trophic structure pie chart
ax5 = axes[1, 1]
trophic_biomass_sorted = trophic_biomass.sort_values('biomass_proportion', ascending=False)
ax5.pie(trophic_biomass_sorted['biomass_proportion'],
        labels=trophic_biomass_sorted.index,
        autopct='%1.1f%%',
        colors=ocean_colors[:len(trophic_biomass_sorted)])
ax5.set_title('Biomass by Trophic Group')

# 6. Latitudinal gradient
ax6 = axes[1, 2]
lat_data = surveys.groupby('lat_bin').agg({
    'total_biomass': 'mean',
    'species_richness': 'mean'
})

ax6_twin = ax6.twinx()
ax6.bar(lat_data.index, lat_data['total_biomass'], color='#0077B6', alpha=0.7,
        label='Biomass')
ax6_twin.plot(lat_data.index, lat_data['species_richness'], 'ro-',
              label='Richness')
ax6.set_xlabel('Latitude (°N)')
ax6.set_ylabel('Mean Biomass (ton/ha)', color='#0077B6')
ax6_twin.set_ylabel('Species Richness', color='red')
ax6.set_title('Latitudinal Gradient')

plt.tight_layout()
plt.savefig('ltem_biomass_productivity.png', dpi=300, bbox_inches='tight')
plt.show()
```

### 10. Generate Report

Use the `LTEMReportGenerator` class to create comprehensive, publication-quality biomass and environmental analysis reports following the CBMC format.

```python
# Import report generator
from chatmpa.report import (
    LTEMReportGenerator,
    generate_environmental_context,
    generate_conclusion_section,
)

# Key statistics
total_biomass = surveys['total_biomass'].sum()
mean_biomass = surveys['total_biomass'].mean()
sst_range = f"{surveys['mean_sst'].min():.1f}-{surveys['mean_sst'].max():.1f}"
chl_range = f"{surveys['mean_chl'].min():.2f}-{surveys['mean_chl'].max():.2f}"

# Top correlations
sig_corrs = env_corr[env_corr['significant']].sort_values('spearman_rho',
                                                           key=abs,
                                                           ascending=False)

# Create comprehensive LTEM biomass report
report = LTEMReportGenerator(
    title="Análisis de Biomasa, Productividad y Factores Ambientales",
    region="Golfo de California",
    period=f"{surveys['year'].min()}-{surveys['year'].max()}",
    language="es"  # or "en" for English
)

# Add authors
report.add_author("Fabio Favoretto", "Ph.D.", "CBMC", "author")

# Add dataset overview as introduction
overview = f"""Este informe presenta el análisis de biomasa de peces, productividad y su
relación con variables ambientales (temperatura superficial del mar y clorofila-a)
utilizando datos del programa LTEM en el Golfo de California.

### Resumen del conjunto de datos

| Métrica | Valor |
|---------|-------|
| Total de muestreos | {len(surveys):,} |
| Biomasa total | {total_biomass:.2f} ton/ha |
| Biomasa media por muestreo | {mean_biomass:.2f} ton/ha |
| Rango de SST | {sst_range} °C |
| Rango de clorofila | {chl_range} mg/m³ |
"""
report.add_section("Resumen del estudio", overview, "introduction")

# Add environmental context section
env_content = generate_environmental_context(ltem)
report.add_section("Contexto ambiental", env_content, "results")

# Add biomass distribution section
regional_summary = surveys.groupby('region')['total_biomass'].agg(['mean', 'std', 'count']).round(2)
depth_summary = surveys.groupby('depth')['total_biomass'].agg(['mean', 'std', 'count']).round(2)

biomass_section = f"""### Distribución de biomasa

#### Por Región

{regional_summary.to_markdown()}

#### Por Profundidad

{depth_summary.to_markdown()}

La variación de biomasa entre regiones es estadísticamente significativa (prueba de Kruskal-Wallis),
indicando patrones espaciales importantes en la distribución de peces.
"""
report.add_section("Distribución de biomasa", biomass_section, "results")

# Add trophic biomass section
trophic_section = f"""### Biomasa por grupo trófico

{trophic_biomass.round(2).to_markdown()}

La estructura trófica del ensamble de peces está dominada por {trophic_biomass['biomass_proportion'].idxmax()},
lo cual tiene implicaciones importantes para el funcionamiento del ecosistema.
"""
report.add_section("Estructura trófica", trophic_section, "results")

# Add environmental correlations section
sst_corr_direction = 'positiva' if env_corr[env_corr['env_variable']=='mean_sst']['spearman_rho'].mean() > 0 else 'negativa'
chl_significant = any(sig_corrs['env_variable']=='mean_chl') if len(sig_corrs) > 0 else False

corr_section = f"""### Correlaciones ambientales

#### Correlaciones significativas (p < 0.05)

{sig_corrs[['fish_variable', 'env_variable', 'spearman_rho', 'p_value']].round(3).to_markdown(index=False) if len(sig_corrs) > 0 else 'No se encontraron correlaciones significativas.'}

#### Matriz de correlación

La matriz de correlación de Spearman muestra las relaciones entre variables de peces y ambientales:

| Relación | Interpretación |
|----------|----------------|
| SST - Biomasa | Correlación {sst_corr_direction} |
| Chl-a - Productividad | {'Significativa' if chl_significant else 'No significativa'} |

Las correlaciones con la clorofila-a reflejan potenciales efectos bottom-up
(control por productividad primaria) sobre la comunidad de peces.
"""
report.add_section("Correlaciones ambientales", corr_section, "results")

# Add SST-biomass relationship section
sst_section = f"""### Relación SST-Biomasa

{sst_analysis.to_markdown() if 'sst_analysis' in dir() else 'Ver análisis detallado en la sección de código.'}

La temperatura superficial del mar (SST) influye en la distribución y abundancia de peces
a través de efectos directos sobre el metabolismo y efectos indirectos sobre la productividad del ecosistema.
"""
report.add_section("Relación temperatura-biomasa", sst_section, "results")

# Add latitudinal gradient section if available
if 'lat_results' in dir():
    lat_section = f"""### Gradiente latitudinal

{lat_results.to_markdown() if lat_results is not None else 'Ver análisis detallado en la sección de código.'}

Los patrones latitudinales reflejan el gradiente ambiental del Golfo de California,
con transiciones entre condiciones templadas en el norte y tropicales en el sur.
"""
    report.add_section("Gradiente latitudinal", lat_section, "results")

# Add figures
report.add_figure('ltem_biomass_productivity.png',
                  'Análisis de biomasa y productividad incluyendo distribución regional, correlaciones ambientales y estructura trófica')

# Add conclusion
dominant_trophic = trophic_biomass['biomass_proportion'].idxmax()

conclusion = generate_conclusion_section(
    key_findings=[
        f"La biomasa media por muestreo es {mean_biomass:.2f} ton/ha",
        "La biomasa varía significativamente entre regiones (Kruskal-Wallis significativo)",
        f"La SST muestra correlación {sst_corr_direction} con la biomasa",
        f"La clorofila-a {'está' if chl_significant else 'no está'} significativamente correlacionada con la productividad",
        f"La comunidad de peces está dominada por {dominant_trophic}"
    ],
    recommendations=[
        "Considerar la variabilidad ambiental al comparar sitios",
        "Incorporar efectos de SST en análisis de tendencias temporales",
        "Investigar la clorofila como factor bottom-up de productividad",
        "Evaluar cambios en estructura trófica bajo escenarios de cambio climático",
        "Integrar variables ambientales en modelos de distribución de especies"
    ]
)
report.add_section("Conclusión", conclusion, "conclusion")

# Add key references
report.add_reference("Favoretto, F., et al. (2024). Trophic restructuring and warming-driven tropicalization in Gulf of California rocky reefs. Global Change Biology.")
report.add_reference("Graham, N. A. J., et al. (2017). Changing role of coral reef fish functional groups along a disturbance-recovery gradient. Ecology and Evolution.")
report.add_reference("Woodson, C. B., et al. (2019). Human impacts and trophic downgrading on coral reefs. Science Advances.")

# Generate final report
paths = report.export_all(
    output_dir="output/",
    base_name="ltem_biomass_report",
    figures_dir="output/figures",
)
print("Reports generated:", paths)
```

## References

- **`../ltem-fish-community/references/report_template.py`** - CBMC-format report generator module with `LTEMReportGenerator` class
- **`references/production_ecology.md`** - Fish production and turnover theory
- **`references/environmental_drivers.md`** - Temperature and chlorophyll effects on fish
- **`references/latitudinal_gradients.md`** - Marine biodiversity gradients

## Success Criteria

A successful biomass/environmental analysis includes:
- [ ] Biomass aggregated and summarized by survey
- [ ] Regional and depth comparisons completed
- [ ] Trophic-level biomass analyzed
- [ ] Environmental correlations calculated
- [ ] SST-biomass relationship characterized
- [ ] Chlorophyll-productivity relationship examined
- [ ] At least 6 visualizations created
- [ ] Comprehensive report generated
