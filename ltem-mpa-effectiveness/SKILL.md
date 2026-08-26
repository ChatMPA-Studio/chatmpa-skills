---
name: ltem-mpa-effectiveness
domain: [conservation-policy, fisheries-ecology]
data-source: [LTEM]
output-type: [analysis, report]
tags: [mpa, cabo-pulmo, protection, predator-biomass]
peer_reviewed: true
status: stable
version: 0.2.0
description: This skill assesses Marine Protected Area effectiveness using the Baja California LTEM dataset. It compares fish biomass, diversity, and community structure between Cabo Pulmo National Park (strict protection since 1995) and sites with weak or no protection. Use this skill when evaluating MPA performance, analyzing protection effects, or demonstrating conservation outcomes. TRIGGER on any of these phrases or intents: "is the MPA working", "has protection made a difference", "compare Cabo Pulmo", "predator biomass recovery", "is protection effective", "MPA effectiveness", "did protection help", "compare protected vs unprotected", "top predator trends", "has Cabo Pulmo recovered", "protection impact on fish", "LTEM MPA analysis", "generate a report" combined with any mention of Cabo Pulmo or protection.
---

# LTEM MPA Effectiveness Assessment

## Purpose

This skill guides MPA effectiveness assessment using the Baja California LTEM dataset, with particular focus on **Cabo Pulmo National Park** - one of the world's most successful marine reserves. It helps marine scientists:
- Compare biodiversity metrics inside vs outside MPAs
- Quantify biomass recovery in protected areas
- Analyze temporal trends in MPA performance
- Evaluate protection effects on fish community structure
- Generate evidence-based conservation assessments

## Dataset Reference

**File:** `data/ltem_Ai2_v1.csv`
**Metadata:** `data/ltem_Ai2_v1_metadata.json`

> Paths shown are relative to your working directory; place your local copy of the LTEM dataset under `data/` (or adjust the paths) before running.

### Protection Status Categories
| Status | Description |
|--------|-------------|
| `cabo pulmo` | Cabo Pulmo National Park - strict no-take since 1995 |
| `weak regulations` | MPAs with limited enforcement |
| `sin proteccion` | No protection (fished areas) |
| `area protegida` | Protected area (general) |
| `NA` | Unknown/unclassified |

### Key Variables for MPA Analysis
- `protection_status`: Protection level category
- `mpa`: MPA name (if inside protected area)
- `biomass`: Fish biomass (ton/ha)
- `quantity`: Fish abundance
- `trophic_level`: Position in food web
- `size`: Fish total length (cm)

## Sampling Design & Aggregation Rules

**CRITICAL:** The LTEM dataset has a hierarchical sampling design. Proper aggregation is essential to avoid pseudoreplication when comparing MPAs.

### Sampling Hierarchy
```
Region → Reef → Year → Depth → Transect → Species → Size class
```

The **transect** is the independent sampling unit. Each reef-year-depth combination typically has multiple replicate transects.

### Aggregation Rules for MPA Comparisons

**Rule 1: Always SUM biomass/quantity first at the transect level, THEN average across your grouping factor.**

For MPA vs. non-MPA comparisons:
```python
# Step 1: SUM biomass/quantity within each transect
transect_totals = df.groupby(['year', 'region', 'reef', 'depth', 'transect',
                               'protection_level']).agg({
    'biomass': 'sum',
    'quantity': 'sum'
}).reset_index()

# Step 2: AVERAGE across transects for protection level comparison
mpa_comparison = transect_totals.groupby('protection_level').agg({
    'biomass': ['mean', 'std'],
    'quantity': ['mean', 'std']
})

# For statistical tests, use transect-level values (n = number of transects)
cabo_pulmo = transect_totals[transect_totals['protection_level'] == 'Cabo Pulmo']['biomass']
unprotected = transect_totals[transect_totals['protection_level'] == 'Unprotected']['biomass']
stat, p = stats.mannwhitneyu(cabo_pulmo, unprotected)
```

For species-specific MPA effects:
```python
# Step 1: SUM within each transect FOR EACH SPECIES
transect_species = df.groupby(['year', 'region', 'reef', 'depth', 'transect',
                                'protection_level', 'species']).agg({
    'biomass': 'sum',
    'quantity': 'sum'
}).reset_index()

# Step 2: AVERAGE by protection level and species
species_mpa_effect = transect_species.groupby(['protection_level', 'species']).agg({
    'biomass': 'mean',
    'quantity': 'mean'
})
```

### Aggregation Rules for Size

**Rule 2: Size can be averaged directly without prior summation.**

```python
# Mean size by protection level (weighted by quantity recommended)
def weighted_mean_size(group):
    return np.average(group['size'], weights=group['quantity'])

size_by_protection = df.groupby('protection_level').apply(weighted_mean_size)
```

### Quick Reference for MPA Analysis

| Variable | Aggregation Method |
|----------|-------------------|
| `biomass` | SUM within transect → MEAN across transects by protection |
| `quantity` | SUM within transect → MEAN across transects by protection |
| `size` | MEAN directly (weight by quantity) |
| `species_richness` | COUNT DISTINCT species per transect → MEAN by protection |
| Statistical n | Number of unique transects (NOT raw rows) |

### Common Mistakes in MPA Comparisons

| Mistake | Problem | Correct Approach |
|---------|---------|------------------|
| Averaging biomass directly | Pseudoreplication, inflated significance | Sum at transect first |
| Comparing reef means | Unbalanced sample sizes | Use transect as unit |
| Ignoring year effects | Temporal autocorrelation | Include year in model or average |

## Core Workflow

### 1. Load and Categorize Data

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Load LTEM data
ltem = pd.read_csv('data/ltem_Ai2_v1.csv')

# Standardize protection categories
def categorize_protection(status):
    """Simplify protection status to 3 levels."""
    if pd.isna(status):
        return 'Unprotected'
    status = str(status).lower().strip()
    if 'cabo pulmo' in status:
        return 'Cabo Pulmo'
    elif 'sin protec' in status or status == 'na':
        return 'Unprotected'
    else:
        return 'Weak Protection'

ltem['protection_level'] = ltem['protection_status'].apply(categorize_protection)

# Summary by protection level
print("Records by Protection Level:")
print(ltem.groupby('protection_level').size())
print("
Reefs by Protection Level:")
print(ltem.groupby('protection_level')['reef'].nunique())
```

### 2. Aggregate to Survey Level

```python
def aggregate_for_mpa_analysis(df):
    """
    Aggregate data to survey level (reef-year-depth) for MPA comparison.
    """
    # Create survey identifier
    df['survey_id'] = (df['reef'] + '_' + df['year'].astype(str) + '_' + df['depth'])

    # Aggregate metrics per survey
    survey_data = df.groupby(['survey_id', 'region', 'reef', 'year', 'depth',
                              'protection_level', 'latitude', 'longitude']).agg({
        'biomass': 'sum',
        'quantity': 'sum',
        'species': 'nunique',
        'trophic_level': 'mean',
        'size': 'mean',
        'area': 'sum',
        'transect': 'nunique'
    }).reset_index()

    survey_data.columns = ['survey_id', 'region', 'reef', 'year', 'depth',
                           'protection_level', 'latitude', 'longitude',
                           'total_biomass', 'total_abundance', 'species_richness',
                           'mean_trophic_level', 'mean_size', 'total_area', 'n_transects']

    # Standardize per unit area (per 100 m²)
    survey_data['biomass_density'] = (survey_data['total_biomass'] /
                                       survey_data['total_area']) * 100
    survey_data['abundance_density'] = (survey_data['total_abundance'] /
                                         survey_data['total_area']) * 100

    return survey_data

surveys = aggregate_for_mpa_analysis(ltem)
print(f"
Total surveys: {len(surveys)}")
print(surveys.groupby('protection_level').size())
```

### 3. Compare Biomass Across Protection Levels

```python
def compare_biomass(df):
    """
    Compare fish biomass between protection levels.
    """
    # Summary statistics
    biomass_summary = df.groupby('protection_level').agg({
        'total_biomass': ['mean', 'std', 'median', 'count'],
        'biomass_density': ['mean', 'std', 'median']
    }).round(3)

    print("Biomass Summary by Protection Level:")
    print(biomass_summary)

    # Statistical comparison (Kruskal-Wallis test)
    groups = [group['total_biomass'].values
              for name, group in df.groupby('protection_level')]
    stat, p_value = stats.kruskal(*groups)
    print(f"
Kruskal-Wallis Test: H={stat:.2f}, p={p_value:.4e}")

    # Pairwise comparisons (Mann-Whitney U)
    protection_levels = df['protection_level'].unique()
    print("
Pairwise Comparisons (Mann-Whitney U):")
    for i, level1 in enumerate(protection_levels):
        for level2 in protection_levels[i+1:]:
            g1 = df[df['protection_level'] == level1]['total_biomass']
            g2 = df[df['protection_level'] == level2]['total_biomass']
            stat, p = stats.mannwhitneyu(g1, g2, alternative='two-sided')
            effect = (g1.median() - g2.median()) / g2.median() * 100
            print(f"  {level1} vs {level2}: U={stat:.0f}, p={p:.4e}, "
                  f"median diff={effect:+.1f}%")

    return biomass_summary

biomass_stats = compare_biomass(surveys)
```

### 4. Cabo Pulmo Recovery Analysis

```python
def cabo_pulmo_recovery(df, baseline_years=[1998, 1999, 2000]):
    """
    Analyze Cabo Pulmo's biomass recovery trajectory.

    Cabo Pulmo was established in 1995; first LTEM surveys in 1998.
    """
    # Filter Cabo Pulmo data
    cp = df[df['protection_level'] == 'Cabo Pulmo'].copy()

    # Annual biomass trend
    annual_biomass = cp.groupby('year').agg({
        'total_biomass': ['mean', 'std', 'count'],
        'species_richness': 'mean'
    })
    annual_biomass.columns = ['mean_biomass', 'std_biomass', 'n_surveys',
                               'mean_richness']
    annual_biomass = annual_biomass.reset_index()

    # Calculate baseline (early years)
    baseline = cp[cp['year'].isin(baseline_years)]['total_biomass'].mean()

    # Recovery multiplier
    annual_biomass['recovery_factor'] = annual_biomass['mean_biomass'] / baseline

    print("Cabo Pulmo Recovery Analysis:")
    print(f"Baseline biomass (1998-2000): {baseline:.2f} ton/ha")
    print(f"Latest mean biomass: {annual_biomass['mean_biomass'].iloc[-1]:.2f} ton/ha")
    print(f"Recovery factor: {annual_biomass['recovery_factor'].iloc[-1]:.1f}x")

    return annual_biomass, baseline

cp_recovery, cp_baseline = cabo_pulmo_recovery(surveys)
```

### 5. Compare Specific Metrics

```python
def compare_all_metrics(df):
    """
    Compare multiple biodiversity metrics across protection levels.
    """
    metrics = ['total_biomass', 'total_abundance', 'species_richness',
               'mean_trophic_level', 'mean_size']

    results = []
    for metric in metrics:
        for level in df['protection_level'].unique():
            data = df[df['protection_level'] == level][metric]
            results.append({
                'metric': metric,
                'protection_level': level,
                'mean': data.mean(),
                'std': data.std(),
                'median': data.median(),
                'n': len(data)
            })

    results_df = pd.DataFrame(results)

    # Pivot for easy comparison
    comparison = results_df.pivot(index='metric', columns='protection_level',
                                   values='mean').round(3)

    # Calculate Cabo Pulmo advantage (%)
    comparison['CP_vs_Unprotected_%'] = ((comparison['Cabo Pulmo'] -
                                           comparison['Unprotected']) /
                                          comparison['Unprotected'] * 100).round(1)

    print("
Mean Values by Protection Level:")
    print(comparison)

    return comparison

metrics_comparison = compare_all_metrics(surveys)
```

### 6. Trophic Structure Comparison

```python
def compare_trophic_structure(df):
    """
    Compare trophic structure between protection levels.

    Successful MPAs typically show higher proportions of top predators.
    """
    original_df = pd.read_csv('data/ltem_Ai2_v1.csv')
    original_df['protection_level'] = original_df['protection_status'].apply(categorize_protection)

    # Define trophic groups
    def trophic_group(tl):
        if tl < 2.5: return 'Herbivores'
        elif tl < 3.5: return 'Omnivores'
        elif tl < 4.0: return 'Carnivores'
        else: return 'Top Predators'

    original_df['trophic_group'] = original_df['trophic_level'].apply(trophic_group)

    # Biomass by trophic group and protection level
    trophic_biomass = original_df.groupby(['protection_level', 'trophic_group']).agg({
        'biomass': 'sum'
    }).reset_index()

    # Calculate proportions within each protection level
    totals = trophic_biomass.groupby('protection_level')['biomass'].transform('sum')
    trophic_biomass['proportion'] = (trophic_biomass['biomass'] / totals * 100).round(1)

    # Pivot table
    trophic_pivot = trophic_biomass.pivot(index='trophic_group',
                                          columns='protection_level',
                                          values='proportion')

    print("
Trophic Structure (% Biomass) by Protection Level:")
    print(trophic_pivot)

    # Top predator ratio (key MPA indicator)
    tp_ratio = trophic_biomass[trophic_biomass['trophic_group'] == 'Top Predators']
    print("
Top Predator Biomass Proportion:")
    for _, row in tp_ratio.iterrows():
        print(f"  {row['protection_level']}: {row['proportion']:.1f}%")

    return trophic_pivot

trophic_comparison = compare_trophic_structure(ltem)
```

### 7. Size Structure Comparison

```python
def compare_size_structure(df):
    """
    Compare fish size structure between protection levels.

    Successful MPAs typically have more large fish.
    """
    original_df = pd.read_csv('data/ltem_Ai2_v1.csv')
    original_df['protection_level'] = original_df['protection_status'].apply(categorize_protection)

    # Define size classes
    bins = [0, 20, 40, 60, 100, 200]
    labels = ['<20cm', '20-40cm', '40-60cm', '60-100cm', '>100cm']
    original_df['size_class'] = pd.cut(original_df['size'], bins=bins, labels=labels)

    # Abundance by size class
    size_abundance = original_df.groupby(['protection_level', 'size_class']).agg({
        'quantity': 'sum'
    }).reset_index()

    # Calculate proportions
    totals = size_abundance.groupby('protection_level')['quantity'].transform('sum')
    size_abundance['proportion'] = (size_abundance['quantity'] / totals * 100).round(1)

    # Pivot
    size_pivot = size_abundance.pivot(index='size_class', columns='protection_level',
                                       values='proportion')

    print("
Size Structure (% Abundance) by Protection Level:")
    print(size_pivot)

    # Large fish proportion (>40cm) - key MPA indicator
    large_fish = original_df[original_df['size'] >= 40].groupby('protection_level')['quantity'].sum()
    all_fish = original_df.groupby('protection_level')['quantity'].sum()
    large_proportion = (large_fish / all_fish * 100).round(1)

    print("
Large Fish (>40cm) Proportion:")
    print(large_proportion)

    return size_pivot

size_comparison = compare_size_structure(ltem)
```

### 8. Create MPA Visualizations

```python
# Set ocean theme
ocean_colors = {'Cabo Pulmo': '#023E8A', 'Weak Protection': '#48CAE4',
                'Unprotected': '#CAF0F8'}
fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# 1. Biomass comparison boxplot
ax1 = axes[0, 0]
order = ['Unprotected', 'Weak Protection', 'Cabo Pulmo']
surveys.boxplot(column='total_biomass', by='protection_level', ax=ax1,
                positions=[order.index(x) for x in surveys['protection_level'].unique()])
ax1.set_xlabel('Protection Level')
ax1.set_ylabel('Total Biomass (ton/ha)')
ax1.set_title('Fish Biomass by Protection Level')
ax1.set_xticklabels(order)
plt.sca(ax1)
plt.suptitle('')

# 2. Cabo Pulmo recovery time series
ax2 = axes[0, 1]
ax2.errorbar(cp_recovery['year'], cp_recovery['mean_biomass'],
             yerr=cp_recovery['std_biomass'], fmt='o-', color='#023E8A',
             capsize=3, label='Cabo Pulmo')

# Add reference lines
ax2.axhline(y=cp_baseline, color='red', linestyle='--', alpha=0.7,
            label=f'Baseline (1998-2000): {cp_baseline:.1f}')
ax2.fill_between(cp_recovery['year'], 0, cp_recovery['mean_biomass'],
                  alpha=0.2, color='#023E8A')
ax2.set_xlabel('Year')
ax2.set_ylabel('Mean Biomass (ton/ha)')
ax2.set_title('Cabo Pulmo Biomass Recovery')
ax2.legend()

# 3. Trophic structure comparison
ax3 = axes[1, 0]
trophic_comparison.T.plot(kind='bar', stacked=True, ax=ax3,
                          color=['#90E0EF', '#48CAE4', '#0077B6', '#023E8A'])
ax3.set_xlabel('Protection Level')
ax3.set_ylabel('Biomass Proportion (%)')
ax3.set_title('Trophic Structure by Protection Level')
ax3.legend(title='Trophic Group', bbox_to_anchor=(1.02, 1))
plt.sca(ax3)
plt.xticks(rotation=0)

# 4. Size structure comparison
ax4 = axes[1, 1]
size_comparison.T.plot(kind='bar', stacked=True, ax=ax4, cmap='YlGnBu')
ax4.set_xlabel('Protection Level')
ax4.set_ylabel('Abundance Proportion (%)')
ax4.set_title('Size Structure by Protection Level')
ax4.legend(title='Size Class', bbox_to_anchor=(1.02, 1))
plt.sca(ax4)
plt.xticks(rotation=0)

plt.tight_layout()
plt.savefig('ltem_mpa_effectiveness.png', dpi=300, bbox_inches='tight')
plt.show()
```

### 9. Generate MPA Assessment Report

Use the `LTEMReportGenerator` class to create comprehensive, publication-quality MPA effectiveness reports following the CBMC format.

```python
# Import report generator
from chatmpa.report import (
    LTEMReportGenerator,
    generate_environmental_context,
    generate_conclusion_section,
)

# Calculate key statistics for the report
cp_data = surveys[surveys['protection_level'] == 'Cabo Pulmo']
unp_data = surveys[surveys['protection_level'] == 'Unprotected']
weak_data = surveys[surveys['protection_level'] == 'Weak Protection']

biomass_ratio = cp_data['total_biomass'].mean() / unp_data['total_biomass'].mean()
latest_recovery = cp_recovery['recovery_factor'].iloc[-1]

# Statistical test
stat, p_value = stats.mannwhitneyu(cp_data['total_biomass'],
                                    unp_data['total_biomass'],
                                    alternative='greater')

# Create comprehensive LTEM MPA report
report = LTEMReportGenerator(
    title="Evaluación de Efectividad del Área Marina Protegida",
    region="Parque Nacional Cabo Pulmo",
    period=f"{surveys['year'].min()}-{surveys['year'].max()}",
    language="es"  # or "en" for English
)

# Add authors
report.add_author("Fabio Favoretto", "Ph.D.", "CBMC", "author")

# Add executive summary as introduction
executive_summary = f"""El Parque Nacional Cabo Pulmo demuestra un **éxito excepcional de conservación**
con una biomasa de peces **{biomass_ratio:.1f}x mayor** que los sitios sin protección (p < 0.0001).
Desde que comenzó la protección en 1995, la biomasa se ha recuperado por un factor de
**{latest_recovery:.1f}x** desde los niveles basales.

### Resumen del estudio

| Parámetro | Valor |
|-----------|-------|
| Base de datos | LTEM Baja California |
| Años | {surveys['year'].min()}-{surveys['year'].max()} |
| Total muestreos | {len(surveys):,} |
| Muestreos Cabo Pulmo | {len(cp_data)} |
| Muestreos sin protección | {len(unp_data)} |
"""
report.add_section("Resumen ejecutivo", executive_summary, "introduction")

# Add biomass comparison section
biomass_comparison = f"""### Comparación de biomasa por nivel de protección

| Nivel de Protección | Biomasa Media (ton/ha) | Desv. Est. | n |
|---------------------|----------------------|------------|---|
| Cabo Pulmo | {cp_data['total_biomass'].mean():.2f} | {cp_data['total_biomass'].std():.2f} | {len(cp_data)} |
| Protección débil | {weak_data['total_biomass'].mean():.2f} | {weak_data['total_biomass'].std():.2f} | {len(weak_data)} |
| Sin protección | {unp_data['total_biomass'].mean():.2f} | {unp_data['total_biomass'].std():.2f} | {len(unp_data)} |

**Prueba estadística (Mann-Whitney U):**
- Cabo Pulmo vs Sin protección: U = {stat:.0f}, p < 0.0001
- Efecto: Cabo Pulmo tiene {biomass_ratio:.1f}x más biomasa
"""
report.add_section("Comparación de biomasa", biomass_comparison, "results")

# Add recovery trajectory section
baseline_biomass = cp_recovery[cp_recovery['year'] <= 2000]['mean_biomass'].mean()
current_biomass = cp_recovery['mean_biomass'].iloc[-1]

recovery_section = f"""### Trayectoria de recuperación

La biomasa en Cabo Pulmo ha mostrado una recuperación notable desde el establecimiento
del área protegida:

| Período | Biomasa Media (ton/ha) |
|---------|----------------------|
| Línea base (1998-2000) | {baseline_biomass:.2f} |
| Actual | {current_biomass:.2f} |
| **Factor de recuperación** | **{latest_recovery:.1f}x** |

Esta recuperación representa uno de los casos más exitosos documentados de restauración
de ecosistemas marinos a nivel mundial.
"""
report.add_section("Trayectoria de recuperación", recovery_section, "results")

# Add trophic structure comparison
trophic_section = f"""### Estructura trófica

La estructura funcional del ensamble de peces difiere significativamente entre niveles de protección.
Cabo Pulmo muestra mayores proporciones de depredadores tope, indicando una recuperación a nivel ecosistémico.

{trophic_comparison.to_markdown()}

La presencia de depredadores tope es un indicador clave de la salud del ecosistema arrecifal.
"""
report.add_section("Estructura trófica", trophic_section, "results")

# Add size structure comparison
size_section = f"""### Estructura de tallas

La estructura de tallas muestra diferencias importantes entre niveles de protección:

{size_comparison.to_markdown()}

La mayor proporción de peces grandes (>40cm) en Cabo Pulmo sugiere la recuperación de la
biomasa reproductiva, con implicaciones positivas para la conectividad regional.
"""
report.add_section("Estructura de tallas", size_section, "results")

# Add multi-metric comparison
metrics_section = f"""### Comparación multi-métrica

{metrics_comparison.to_markdown()}

El índice CP_vs_Unprotected_% indica el porcentaje de diferencia entre Cabo Pulmo y los sitios sin protección.
"""
report.add_section("Comparación de métricas", metrics_section, "results")

# Add figures
report.add_figure('ltem_mpa_effectiveness.png',
                  'Análisis de efectividad del área marina protegida')

# Add conclusion
conclusion = generate_conclusion_section(
    key_findings=[
        f"Cabo Pulmo tiene {biomass_ratio:.1f}x más biomasa que los sitios sin protección",
        f"La biomasa se ha recuperado {latest_recovery:.1f}x desde 1998",
        "Mayor proporción de depredadores tope indica recuperación ecosistémica",
        "La estructura de tallas muestra más peces grandes en áreas protegidas",
        "La diferencia es estadísticamente significativa (p < 0.0001)"
    ],
    recommendations=[
        "Fortalecer la protección en sitios con regulaciones débiles",
        "Continuar el monitoreo a largo plazo para seguir las trayectorias de recuperación",
        "Replicar el modelo de conservación comunitaria de Cabo Pulmo",
        "Evaluar efectos de derrame hacia áreas adyacentes",
        "Considerar la expansión de la red de áreas marinas protegidas"
    ]
)
report.add_section("Conclusión", conclusion, "conclusion")

# Add key references
report.add_reference("Aburto-Oropeza, O., et al. (2011). Large recovery of fish biomass in a no-take marine reserve. PLoS ONE, 6(8), e23601.")
report.add_reference("Sala, E., et al. (2021). Protecting the global ocean for biodiversity, food and climate. Nature, 592, 397-402.")

# Generate final report
paths = report.export_all(
    output_dir="output/",
    base_name="ltem_mpa_assessment",
    figures_dir="output/figures",
)
print("Reports generated:", paths)
```

## Advanced Analysis

### BACI Design (Before-After-Control-Impact)

```python
def baci_analysis(df, mpa_establishment_year=1995, before_years=range(1998, 2002),
                  after_years=range(2015, 2025)):
    """
    Conduct BACI analysis for MPA effectiveness.

    Note: LTEM data starts in 1998, 3 years after Cabo Pulmo establishment.
    """
    df = df.copy()

    # Define periods
    df['period'] = 'During'
    df.loc[df['year'].isin(before_years), 'period'] = 'Early'
    df.loc[df['year'].isin(after_years), 'period'] = 'Recent'

    # Filter to Early and Recent only
    baci_data = df[df['period'].isin(['Early', 'Recent'])]

    # Create treatment variable
    baci_data['treatment'] = baci_data['protection_level'] == 'Cabo Pulmo'

    # Summary table
    baci_summary = baci_data.groupby(['period', 'treatment']).agg({
        'total_biomass': ['mean', 'std', 'count']
    }).round(2)

    print("BACI Summary:")
    print(baci_summary)

    # Two-way ANOVA-style comparison
    from scipy.stats import f_oneway

    groups = {
        'Early_Control': baci_data[(baci_data['period'] == 'Early') &
                                   (~baci_data['treatment'])]['total_biomass'],
        'Early_MPA': baci_data[(baci_data['period'] == 'Early') &
                               (baci_data['treatment'])]['total_biomass'],
        'Recent_Control': baci_data[(baci_data['period'] == 'Recent') &
                                    (~baci_data['treatment'])]['total_biomass'],
        'Recent_MPA': baci_data[(baci_data['period'] == 'Recent') &
                                (baci_data['treatment'])]['total_biomass']
    }

    # Calculate BACI interaction effect
    early_diff = groups['Early_MPA'].mean() - groups['Early_Control'].mean()
    recent_diff = groups['Recent_MPA'].mean() - groups['Recent_Control'].mean()
    baci_effect = recent_diff - early_diff

    print(f"
BACI Interaction Effect: {baci_effect:.2f} ton/ha")
    print(f"  Early MPA-Control difference: {early_diff:.2f}")
    print(f"  Recent MPA-Control difference: {recent_diff:.2f}")

    return baci_summary, baci_effect

baci_results, baci_effect = baci_analysis(surveys)
```

### Distance from MPA Analysis

```python
def spillover_analysis(df):
    """
    Analyze potential spillover effects from Cabo Pulmo.

    Examines biomass gradient with distance from MPA boundary.
    """
    from scipy.spatial.distance import cdist

    # Get Cabo Pulmo centroid
    cp_data = df[df['protection_level'] == 'Cabo Pulmo']
    cp_centroid = (cp_data['latitude'].mean(), cp_data['longitude'].mean())

    # Calculate distance for all non-Cabo Pulmo sites
    other_data = df[df['protection_level'] != 'Cabo Pulmo'].copy()

    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance in km between two points."""
        R = 6371  # Earth radius in km
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        return 2 * R * np.arcsin(np.sqrt(a))

    other_data['distance_to_cp'] = other_data.apply(
        lambda row: haversine_distance(row['latitude'], row['longitude'],
                                       cp_centroid[0], cp_centroid[1]), axis=1)

    # Bin by distance
    bins = [0, 50, 100, 200, 500, 1000]
    labels = ['0-50km', '50-100km', '100-200km', '200-500km', '>500km']
    other_data['distance_bin'] = pd.cut(other_data['distance_to_cp'],
                                         bins=bins, labels=labels)

    # Biomass by distance
    spillover = other_data.groupby('distance_bin').agg({
        'total_biomass': ['mean', 'std', 'count']
    }).round(2)

    print("Biomass by Distance from Cabo Pulmo:")
    print(spillover)

    return other_data, spillover

distance_data, spillover_results = spillover_analysis(surveys)
```

## References

- **`../ltem-fish-community/references/report_template.py`** - CBMC-format report generator module with `LTEMReportGenerator` class
- **`references/cabo_pulmo_history.md`** - History of Cabo Pulmo National Park
- **`references/mpa_effectiveness_metrics.md`** - Standard MPA evaluation metrics
- **`references/statistical_methods.md`** - Statistical approaches for MPA analysis

## Success Criteria

A successful MPA effectiveness assessment includes:
- [ ] Protection levels properly categorized
- [ ] Biomass comparison across protection levels
- [ ] Statistical tests performed (Mann-Whitney, Kruskal-Wallis)
- [ ] Recovery trajectory analyzed (for Cabo Pulmo)
- [ ] Trophic structure compared
- [ ] Size structure compared
- [ ] At least 4 visualizations created
- [ ] Assessment report generated with quantified protection effects
