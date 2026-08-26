---
name: ltem-fish-community
domain: [fisheries-ecology, biodiversity]
data-source: [LTEM]
output-type: [analysis, report]
tags: [diversity, trophic, size-structure, community, shannon]
peer_reviewed: true
status: stable
version: 0.2.0
description: This skill analyzes fish community structure from the Baja California LTEM (Long-Term Ecological Monitoring) dataset. It calculates diversity indices, species composition, size structure, and trophic metrics. Use this skill when analyzing fish assemblages, comparing communities across sites or regions, or generating biodiversity reports from the LTEM database.
---

# LTEM Fish Community Analysis

## Purpose

This skill guides the analysis of fish community structure using the Baja California LTEM dataset. It helps marine scientists:
- Calculate diversity indices (Shannon, Simpson, species richness)
- Analyze species composition and relative abundance
- Examine size structure and recruitment patterns
- Evaluate trophic structure of fish assemblages
- Compare communities across regions and depth strata
- Generate publication-quality visualizations and reports

## Dataset Reference

**File:** `data/ltem_Ai2_v1.csv`
**Metadata:** `data/ltem_Ai2_v1_metadata.json`

> Paths shown are relative to your working directory; place your local copy of the LTEM dataset under `data/` (or adjust the paths) before running.

### Key Columns for Community Analysis
| Column | Description |
|--------|-------------|
| `species` | Scientific name (genus + species) |
| `genus` | Genus only |
| `quantity` | Number of individuals per size class |
| `size` | Total length (cm) |
| `trophic_level` | Position in food web (2-4.5) |
| `biomass` | Biomass in ton/ha |
| `region` | Geographic region |
| `reef` | Reef name |
| `depth` | Depth stratum (Shallow/Deep) |
| `year` | Survey year |
| `transect` | Replicate transect ID |
| `area` | Survey area (m²) |

## Sampling Design & Aggregation Rules

**CRITICAL:** The LTEM dataset has a hierarchical sampling design. Proper aggregation is essential to avoid pseudoreplication and obtain correct statistical results.

### Sampling Hierarchy
```
Region → Reef → Year → Depth → Transect → Species → Size class
```

The **transect** is the independent sampling unit. Each reef-year-depth combination typically has multiple replicate transects.

### Aggregation Rules for Biomass and Quantity

**Rule 1: Always SUM first at the transect level, THEN average across your grouping factor.**

For community-level analyses (no species grouping):
```python
# Step 1: SUM biomass/quantity within each transect
transect_totals = df.groupby(['year', 'region', 'reef', 'depth', 'transect']).agg({
    'biomass': 'sum',
    'quantity': 'sum'
}).reset_index()

# Step 2: AVERAGE across transects for your comparison
# Example: Compare regions
regional_means = transect_totals.groupby('region').agg({
    'biomass': 'mean',
    'quantity': 'mean'
})
```

For species/group-specific analyses:
```python
# Step 1: SUM biomass/quantity within each transect FOR EACH SPECIES/GROUP
transect_species = df.groupby(['year', 'region', 'reef', 'depth', 'transect', 'species']).agg({
    'biomass': 'sum',
    'quantity': 'sum'
}).reset_index()

# Step 2: AVERAGE across transects for your comparison
species_means = transect_species.groupby(['region', 'species']).agg({
    'biomass': 'mean',
    'quantity': 'mean'
})
```

### Aggregation Rules for Size

**Rule 2: Size can be averaged directly without prior summation.**

```python
# Size can be averaged directly (weighted by quantity if needed)
mean_size = df.groupby('region')['size'].mean()

# Or weighted mean for more accuracy
def weighted_mean_size(group):
    return np.average(group['size'], weights=group['quantity'])

weighted_size = df.groupby('region').apply(weighted_mean_size)
```

### Common Mistakes to Avoid

| Mistake | Problem | Correct Approach |
|---------|---------|------------------|
| Averaging biomass directly | Treats each row as independent, inflating n | Sum at transect level first |
| Using raw row count as n | Pseudoreplication | Count unique transects |
| Ignoring depth stratification | Confounds depth effects | Include depth in grouping |
| Mixing size classes in biomass | Already summed in data | Check data structure first |

### Quick Reference Table

| Variable | Aggregation Method |
|----------|-------------------|
| `biomass` | SUM within transect → MEAN across transects |
| `quantity` | SUM within transect → MEAN across transects |
| `size` | MEAN directly (optionally weight by quantity) |
| `trophic_level` | MEAN (weighted by biomass for community-level) |
| `species_richness` | COUNT DISTINCT after transect aggregation |

## Core Workflow

### 1. Load and Prepare Data

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Load LTEM data
ltem = pd.read_csv('data/ltem_Ai2_v1.csv')

print(f"Total records: {len(ltem):,}")
print(f"Years: {ltem['year'].min()}-{ltem['year'].max()}")
print(f"Regions: {ltem['region'].nunique()}")
print(f"Reefs: {ltem['reef'].nunique()}")
print(f"Species: {ltem['species'].nunique()}")
```

### 2. Aggregate to Survey Level

```python
def aggregate_to_survey(df):
    """
    Aggregate fish observations to survey level (reef-year-depth).

    Returns DataFrame with one row per species per survey.
    """
    # Create survey identifier
    df['survey_id'] = (df['region'] + '_' + df['reef'] + '_' +
                       df['year'].astype(str) + '_' + df['depth'])

    # Aggregate across transects
    survey_data = df.groupby(['survey_id', 'region', 'reef', 'year',
                              'depth', 'latitude', 'longitude',
                              'protection_status', 'species']).agg({
        'quantity': 'sum',
        'biomass': 'sum',
        'trophic_level': 'first',
        'genus': 'first',
        'area': 'sum',  # Total area surveyed
        'transect': 'nunique'  # Number of transects
    }).reset_index()

    # Calculate density (individuals per 100 m²)
    survey_data['density'] = (survey_data['quantity'] / survey_data['area']) * 100

    return survey_data

survey_df = aggregate_to_survey(ltem)
print(f"Surveys: {survey_df['survey_id'].nunique()}")
```

### 3. Calculate Diversity Indices

```python
def calculate_diversity_metrics(df, group_cols=['survey_id']):
    """
    Calculate diversity metrics for each survey or group.

    Returns DataFrame with:
    - species_richness: Number of species
    - total_abundance: Total number of individuals
    - total_biomass: Total biomass
    - shannon_index: Shannon-Wiener H'
    - simpson_index: Simpson's 1-D
    - pielou_evenness: J'
    """

    def calc_metrics(group):
        abundances = group['quantity'].values
        n_total = abundances.sum()

        if n_total == 0:
            return pd.Series({
                'species_richness': 0,
                'total_abundance': 0,
                'total_biomass': 0,
                'shannon_index': 0,
                'simpson_index': 0,
                'pielou_evenness': 0
            })

        # Proportions
        p = abundances / n_total
        p = p[p > 0]

        # Species richness
        S = len(p)

        # Shannon index
        H = -np.sum(p * np.log(p))

        # Simpson index
        D = 1 - np.sum(p ** 2)

        # Pielou evenness
        J = H / np.log(S) if S > 1 else 0

        return pd.Series({
            'species_richness': S,
            'total_abundance': n_total,
            'total_biomass': group['biomass'].sum(),
            'shannon_index': round(H, 3),
            'simpson_index': round(D, 3),
            'pielou_evenness': round(J, 3)
        })

    diversity = df.groupby(group_cols).apply(calc_metrics).reset_index()
    return diversity

# Calculate diversity per survey
diversity_df = calculate_diversity_metrics(survey_df)

# Add survey metadata
survey_meta = survey_df.groupby('survey_id').agg({
    'region': 'first',
    'reef': 'first',
    'year': 'first',
    'depth': 'first',
    'protection_status': 'first',
    'latitude': 'first',
    'longitude': 'first'
}).reset_index()

diversity_df = diversity_df.merge(survey_meta, on='survey_id')

print("
Diversity Summary by Region:")
print(diversity_df.groupby('region')[['species_richness', 'shannon_index',
                                       'total_biomass']].mean().round(2))
```

### 4. Species Composition Analysis

```python
def species_composition(df, group_col='region', top_n=15):
    """
    Analyze species composition and dominance.

    Returns top species by abundance and biomass.
    """
    # Total abundance by species and group
    abundance = df.groupby([group_col, 'species'])['quantity'].sum().reset_index()

    # Calculate relative abundance within each group
    totals = abundance.groupby(group_col)['quantity'].transform('sum')
    abundance['relative_abundance'] = (abundance['quantity'] / totals) * 100

    # Get top species per group
    top_species = (abundance.sort_values([group_col, 'quantity'], ascending=[True, False])
                   .groupby(group_col)
                   .head(top_n))

    return top_species

# Get species composition by region
composition = species_composition(survey_df, group_col='region', top_n=10)

# Pivot for visualization
comp_pivot = composition.pivot(index='species', columns='region',
                                values='relative_abundance').fillna(0)
```

### 5. Trophic Structure Analysis

```python
def trophic_structure(df, group_col='region'):
    """
    Analyze trophic structure of fish communities.

    Trophic levels:
    - 2.0-2.5: Herbivores
    - 2.5-3.5: Omnivores/Low carnivores
    - 3.5-4.0: Mid-level carnivores
    - 4.0+: Top predators
    """
    # Define trophic groups
    def assign_trophic_group(tl):
        if tl < 2.5:
            return 'Herbivores'
        elif tl < 3.5:
            return 'Omnivores'
        elif tl < 4.0:
            return 'Carnivores'
        else:
            return 'Top Predators'

    df = df.copy()
    df['trophic_group'] = df['trophic_level'].apply(assign_trophic_group)

    # Biomass by trophic group
    trophic_biomass = df.groupby([group_col, 'trophic_group']).agg({
        'biomass': 'sum',
        'quantity': 'sum'
    }).reset_index()

    # Calculate proportions
    totals = trophic_biomass.groupby(group_col)['biomass'].transform('sum')
    trophic_biomass['biomass_proportion'] = (trophic_biomass['biomass'] / totals) * 100

    return trophic_biomass

trophic_df = trophic_structure(survey_df, group_col='region')
print("
Trophic Structure (% Biomass) by Region:")
print(trophic_df.pivot(index='trophic_group', columns='region',
                       values='biomass_proportion').round(1))
```

### 6. Size Structure Analysis

```python
def size_structure(df, group_col='region', bins=[0, 10, 20, 30, 50, 100, 200]):
    """
    Analyze size structure of fish communities.

    Default bins represent ecologically meaningful size classes:
    - 0-10 cm: Recruits/juveniles
    - 10-20 cm: Small adults
    - 20-30 cm: Medium
    - 30-50 cm: Large
    - 50-100 cm: Very large
    - 100+ cm: Giants
    """
    df = df.copy()
    labels = ['0-10', '10-20', '20-30', '30-50', '50-100', '100+']
    df['size_class'] = pd.cut(df['size'], bins=bins, labels=labels)

    # Abundance by size class
    size_abundance = df.groupby([group_col, 'size_class'])['quantity'].sum().reset_index()

    # Calculate proportions
    totals = size_abundance.groupby(group_col)['quantity'].transform('sum')
    size_abundance['proportion'] = (size_abundance['quantity'] / totals) * 100

    return size_abundance

size_df = size_structure(ltem, group_col='region')
print("
Size Structure (% Abundance) by Region:")
print(size_df.pivot(index='size_class', columns='region',
                    values='proportion').round(1))
```

### 7. Create Visualizations

```python
# Set ocean theme colors
ocean_colors = ['#023E8A', '#0077B6', '#00B4D8', '#48CAE4', '#90E0EF', '#CAF0F8', '#00ABC8']
sns.set_palette(ocean_colors)

fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# 1. Species richness by region
ax1 = axes[0, 0]
diversity_df.boxplot(column='species_richness', by='region', ax=ax1)
ax1.set_xlabel('Region')
ax1.set_ylabel('Species Richness')
ax1.set_title('Species Richness by Region')
plt.sca(ax1)
plt.xticks(rotation=45, ha='right')

# 2. Shannon diversity by region and depth
ax2 = axes[0, 1]
diversity_pivot = diversity_df.groupby(['region', 'depth'])['shannon_index'].mean().unstack()
diversity_pivot.plot(kind='bar', ax=ax2, color=ocean_colors[:2])
ax2.set_xlabel('Region')
ax2.set_ylabel('Shannon Index (H\')')
ax2.set_title('Shannon Diversity by Region and Depth')
ax2.legend(title='Depth')
plt.sca(ax2)
plt.xticks(rotation=45, ha='right')

# 3. Trophic structure
ax3 = axes[1, 0]
trophic_pivot = trophic_df.pivot(index='region', columns='trophic_group',
                                  values='biomass_proportion')
trophic_pivot.plot(kind='bar', stacked=True, ax=ax3,
                   color=['#90E0EF', '#48CAE4', '#0077B6', '#023E8A'])
ax3.set_xlabel('Region')
ax3.set_ylabel('Biomass Proportion (%)')
ax3.set_title('Trophic Structure by Region')
ax3.legend(title='Trophic Group', bbox_to_anchor=(1.02, 1))
plt.sca(ax3)
plt.xticks(rotation=45, ha='right')

# 4. Size structure
ax4 = axes[1, 1]
size_pivot = size_df.pivot(index='region', columns='size_class', values='proportion')
size_pivot.plot(kind='bar', stacked=True, ax=ax4, cmap='YlGnBu')
ax4.set_xlabel('Region')
ax4.set_ylabel('Abundance Proportion (%)')
ax4.set_title('Size Structure by Region')
ax4.legend(title='Size Class (cm)', bbox_to_anchor=(1.02, 1))
plt.sca(ax4)
plt.xticks(rotation=45, ha='right')

plt.tight_layout()
plt.savefig('ltem_fish_community_analysis.png', dpi=300, bbox_inches='tight')
plt.show()
```

### 8. Generate Community Report

Use the `LTEMReportGenerator` class to create comprehensive, publication-quality reports following the CBMC format.

```python
# Import report generator
from chatmpa.report import (
    LTEMReportGenerator,
    generate_environmental_context,
    generate_fish_community_section,
    generate_trophic_structure_section,
    generate_conclusion_section,
)

# Create comprehensive LTEM report
report = LTEMReportGenerator(
    title="Análisis de Comunidades de Peces",
    region="Baja California Sur",  # or specific region from data
    period=f"{survey_df['year'].min()}-{survey_df['year'].max()}",
    language="es"  # or "en" for English
)

# Add authors (optional)
report.add_author("Fabio Favoretto", "Ph.D.", "CBMC", "author")

# Add environmental context section (if SST/Chl data available)
if 'mean_sst' in ltem.columns and 'mean_chl' in ltem.columns:
    env_content = generate_environmental_context(ltem)
    report.add_section("Contexto ambiental", env_content, "results")

# Add fish community section
fish_content = generate_fish_community_section(survey_df)
report.add_section("Comunidad de peces", fish_content, "results")

# Add trophic structure section
trophic_content = generate_trophic_structure_section(survey_df)
report.add_section("Estructura trófica", trophic_content, "results")

# Add diversity metrics section
diversity_summary = f"""### Índices de diversidad

Los índices de diversidad muestran variación entre regiones y estratos de profundidad:

#### Por Región

{diversity_df.groupby('region')[['species_richness', 'shannon_index', 'simpson_index', 'total_biomass']].mean().round(2).to_markdown()}

#### Por Estrato de Profundidad

{diversity_df.groupby('depth')[['species_richness', 'shannon_index', 'simpson_index', 'total_biomass']].mean().round(2).to_markdown()}

La diversidad Shannon (H') varía entre {diversity_df['shannon_index'].min():.2f} y {diversity_df['shannon_index'].max():.2f},
indicando heterogeneidad en la estructura de las comunidades.
"""
report.add_section("Diversidad", diversity_summary, "results")

# Add figures
report.add_figure('ltem_fish_community_analysis.png',
                  'Análisis de diversidad y estructura de la comunidad de peces')
report.add_figure('nmds_ordination.png',
                  'Ordenación NMDS de las comunidades de peces por región')

# Calculate key metrics for conclusion
top_abundant = survey_df.groupby('species')['quantity'].sum().sort_values(ascending=False)
top_biomass = survey_df.groupby('species')['biomass'].sum().sort_values(ascending=False)
richest_region = diversity_df.groupby('region')['species_richness'].mean().idxmax()

# Add conclusion
conclusion = generate_conclusion_section(
    key_findings=[
        f"Se registraron {survey_df['species'].nunique()} especies de peces en el estudio",
        f"La región con mayor riqueza de especies es {richest_region}",
        f"La especie dominante por abundancia es {top_abundant.index[0]}",
        f"La especie dominante por biomasa es {top_biomass.index[0]}",
        f"El índice de Shannon varía entre {diversity_df['shannon_index'].min():.2f} y {diversity_df['shannon_index'].max():.2f}"
    ],
    recommendations=[
        "Continuar el monitoreo para detectar cambios temporales en la estructura comunitaria",
        "Evaluar patrones estacionales en las comunidades de peces",
        "Comparar con otros sistemas arrecifales de la región",
        "Investigar los factores ambientales que influyen en la diversidad"
    ]
)
report.add_section("Conclusión", conclusion, "conclusion")

# Add key references
report.add_reference("Aburto-Oropeza, O., et al. (2011). Large recovery of fish biomass in a no-take marine reserve. PLoS ONE, 6(8), e23601.")
report.add_reference("Favoretto, F., et al. (2024). Trophic restructuring and warming-driven tropicalization in Gulf of California rocky reefs. Global Change Biology.")

# Export Markdown + HTML + PDF in one call
paths = report.export_all(
    output_dir="output/",
    base_name="ltem_community_report",
    figures_dir="output/figures",
)
print("Reports generated:", paths)
```

## Analysis Patterns

### Compare Communities (Bray-Curtis Dissimilarity)

```python
from scipy.spatial.distance import braycurtis, pdist, squareform
from scipy.cluster.hierarchy import linkage, dendrogram

def community_dissimilarity(df, group_col='region'):
    """
    Calculate Bray-Curtis dissimilarity between communities.
    """
    # Create species abundance matrix
    abundance_matrix = df.pivot_table(
        index=group_col,
        columns='species',
        values='quantity',
        aggfunc='sum',
        fill_value=0
    )

    # Calculate pairwise distances
    distances = pdist(abundance_matrix.values, metric='braycurtis')
    dist_matrix = squareform(distances)

    # Create distance DataFrame
    dist_df = pd.DataFrame(
        dist_matrix,
        index=abundance_matrix.index,
        columns=abundance_matrix.index
    )

    return dist_df, abundance_matrix

dist_matrix, abundance = community_dissimilarity(survey_df, 'region')
print("Bray-Curtis Dissimilarity Matrix:")
print(dist_matrix.round(3))
```

### NMDS Ordination

```python
from sklearn.manifold import MDS

def nmds_ordination(df, group_col='survey_id', meta_col='region'):
    """
    Perform Non-metric Multidimensional Scaling on community data.
    """
    # Create abundance matrix
    abundance_matrix = df.pivot_table(
        index=group_col,
        columns='species',
        values='quantity',
        aggfunc='sum',
        fill_value=0
    )

    # NMDS
    nmds = MDS(n_components=2, dissimilarity='precomputed', random_state=42)
    distances = squareform(pdist(abundance_matrix.values, metric='braycurtis'))
    coords = nmds.fit_transform(distances)

    # Create result DataFrame
    result = pd.DataFrame({
        'NMDS1': coords[:, 0],
        'NMDS2': coords[:, 1],
        group_col: abundance_matrix.index
    })

    return result

# Plot NMDS
nmds_result = nmds_ordination(survey_df, 'survey_id', 'region')
nmds_result = nmds_result.merge(survey_meta, on='survey_id')

plt.figure(figsize=(10, 8))
for region in nmds_result['region'].unique():
    subset = nmds_result[nmds_result['region'] == region]
    plt.scatter(subset['NMDS1'], subset['NMDS2'], label=region, alpha=0.6)
plt.xlabel('NMDS1')
plt.ylabel('NMDS2')
plt.title('NMDS Ordination of Fish Communities')
plt.legend()
plt.savefig('nmds_ordination.png', dpi=300)
```

## Data Quality Checks

```python
def data_quality_check(df):
    """Run data quality checks on LTEM data."""

    checks = {
        'Total records': len(df),
        'Missing coordinates': df[['latitude', 'longitude']].isna().any(axis=1).sum(),
        'Missing species': df['species'].isna().sum(),
        'Zero quantities': (df['quantity'] == 0).sum(),
        'Negative biomass': (df['biomass'] < 0).sum(),
        'Invalid trophic levels': ((df['trophic_level'] < 2) | (df['trophic_level'] > 5)).sum(),
        'Surveys per year': df.groupby('year')['reef'].nunique().to_dict()
    }

    print("Data Quality Report:")
    print("-" * 40)
    for check, value in checks.items():
        if check != 'Surveys per year':
            print(f"{check}: {value}")

    return checks

quality = data_quality_check(ltem)
```

## References

- **`references/report_template.py`** - CBMC-format report generator module with `LTEMReportGenerator` class
- **`references/diversity_indices.md`** - Detailed explanation of diversity metrics
- **`references/ltem_methodology.md`** - LTEM survey methodology
- The authoritative species list and trait values come from the dataset's own metadata file (`ltem_Ai2_v1_metadata.json`); do not maintain a separate species list here.

## Success Criteria

A successful fish community analysis includes:
- [ ] Data loaded and aggregated to survey level
- [ ] Diversity indices calculated (richness, Shannon, Simpson)
- [ ] Species composition analyzed
- [ ] Trophic structure evaluated
- [ ] Size structure analyzed
- [ ] At least 4 visualizations created
- [ ] Community report generated
- [ ] Regional comparisons completed
