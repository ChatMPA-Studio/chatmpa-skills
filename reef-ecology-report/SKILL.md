---
name: reef-ecology-report
domain: [reef-ecology, biodiversity]
data-source: [field-survey]
output-type: [report]
tags: [coral-cover, bleaching, monitoring, reef-health]
status: stable
version: 0.2.0
description: This skill should be used when creating reef ecology reports, analyzing coral reef data, or documenting marine ecosystem surveys. It provides workflows for loading reef monitoring data, calculating key ecological metrics (coral coverage, species diversity, bleaching indices), creating visualizations, and generating comprehensive reports. Use this skill when the user asks to analyze reef data, create ecology reports, or work with coral monitoring datasets.
---

# Reef Ecology Report Creator

## Purpose

This skill guides the creation of comprehensive reef ecology reports using Python in chatMPA Studio. It helps marine scientists:
- Load and process reef monitoring data (CSV, Excel, databases)
- Calculate key ecological metrics
- Generate publication-quality visualizations
- Export professional reports in multiple formats

## When to Use This Skill

Use this skill when:
- User wants to analyze coral reef survey data
- User asks to calculate reef health metrics
- User needs to create reef monitoring reports
- User wants to visualize coral coverage or species distribution
- User mentions benthic transects, quadrat surveys, or reef assessments

Do NOT use this skill for:
- Open ocean temperature analysis (use `sea-surface-temperature`)
- Species distribution modeling (use `marine-species-analysis`)
- General Python development questions

## Core Workflow

### 1. Set Up Environment

Ensure required packages are installed:

```python
# Core packages for reef analysis
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Optional: for advanced analysis
# pip install scipy scikit-learn geopandas
```

### 2. Load Reef Data

**Common data sources:**
- NOAA Coral Reef Watch
- Reef Check monitoring data
- AIMS Long-term Monitoring Program
- Local survey databases

```python
# Load from CSV
reef_data = pd.read_csv('reef_survey.csv')

# Load from Excel with multiple sheets
surveys = pd.read_excel('monitoring_data.xlsx', sheet_name='Transects')
species = pd.read_excel('monitoring_data.xlsx', sheet_name='Species')

# Preview the data
print(reef_data.head())
print(reef_data.dtypes)
print(reef_data.describe())
```

**Ask user for:**
- Data file location and format
- Survey methodology used
- Key columns for analysis
- Date range of interest

### 3. Calculate Ecological Metrics

**Essential reef metrics:**

```python
# Coral Coverage Calculation
def calculate_coral_coverage(df, coral_column='hard_coral', total_column='total_points'):
    """Calculate percent coral coverage from point intercept data."""
    df['coral_coverage_pct'] = (df[coral_column] / df[total_column]) * 100
    return df

# Species Diversity (Shannon Index)
def shannon_diversity(species_counts):
    """Calculate Shannon diversity index."""
    proportions = species_counts / species_counts.sum()
    proportions = proportions[proportions > 0]  # Remove zeros
    return -np.sum(proportions * np.log(proportions))

# Bleaching Index
def bleaching_severity(df):
    """Calculate bleaching severity index (0-4 scale)."""
    severity_map = {'none': 0, 'pale': 1, 'bleached_1_50': 2,
                    'bleached_50_100': 3, 'dead': 4}
    return df['bleaching_status'].map(severity_map).mean()

# Species Richness
def species_richness(species_df, site_column='site_id', species_column='species'):
    """Count unique species per site."""
    return species_df.groupby(site_column)[species_column].nunique()
```

### 4. Create Visualizations

```python
# Set marine science color palette
ocean_colors = ['#0077B6', '#00B4D8', '#90E0EF', '#CAF0F8', '#023E8A']
sns.set_palette(ocean_colors)

# Coral Coverage by Site
fig, ax = plt.subplots(figsize=(12, 6))
reef_data.groupby('site')['coral_coverage_pct'].mean().plot(kind='bar', ax=ax)
ax.set_xlabel('Survey Site')
ax.set_ylabel('Coral Coverage (%)')
ax.set_title('Mean Coral Coverage by Site')
plt.tight_layout()
plt.savefig('coral_coverage.png', dpi=300)

# Time Series of Reef Health
fig, ax = plt.subplots(figsize=(12, 6))
reef_data.groupby('survey_date')['coral_coverage_pct'].mean().plot(ax=ax)
ax.set_xlabel('Survey Date')
ax.set_ylabel('Coral Coverage (%)')
ax.set_title('Temporal Trend in Coral Coverage')
plt.tight_layout()
plt.savefig('coverage_trend.png', dpi=300)

# Species Composition Pie Chart
species_counts = reef_data.groupby('species_group').size()
fig, ax = plt.subplots(figsize=(10, 10))
ax.pie(species_counts, labels=species_counts.index, autopct='%1.1f%%', colors=ocean_colors)
ax.set_title('Benthic Community Composition')
plt.savefig('species_composition.png', dpi=300)
```

### 5. Generate Report

```python
# Create summary statistics
summary = {
    'Total Sites Surveyed': reef_data['site'].nunique(),
    'Survey Period': f"{reef_data['date'].min()} to {reef_data['date'].max()}",
    'Mean Coral Coverage': f"{reef_data['coral_coverage_pct'].mean():.1f}%",
    'Coverage Range': f"{reef_data['coral_coverage_pct'].min():.1f}% - {reef_data['coral_coverage_pct'].max():.1f}%",
    'Species Richness': reef_data['species'].nunique(),
    'Shannon Diversity': f"{shannon_diversity(species_counts):.2f}"
}

# Export to markdown report
with open('reef_ecology_report.md', 'w') as f:
    f.write('# Reef Ecology Survey Report\n\n')
    f.write('## Survey Summary\n\n')
    for key, value in summary.items():
        f.write(f'- **{key}:** {value}\n')
    f.write('\n## Visualizations\n\n')
    f.write('![Coral Coverage](coral_coverage.png)\n\n')
    f.write('![Coverage Trend](coverage_trend.png)\n\n')
    f.write('![Species Composition](species_composition.png)\n\n')

print("Report generated: reef_ecology_report.md")
```

## Data Format Guidelines

### Expected Data Structure

**Transect Data:**
| Column | Type | Description |
|--------|------|-------------|
| site_id | string | Unique site identifier |
| transect_id | string | Transect identifier |
| date | date | Survey date |
| depth_m | float | Depth in meters |
| hard_coral | int | Hard coral point count |
| soft_coral | int | Soft coral point count |
| algae | int | Algae point count |
| total_points | int | Total points sampled |

**Species Data:**
| Column | Type | Description |
|--------|------|-------------|
| site_id | string | Unique site identifier |
| species | string | Species name |
| count | int | Abundance count |
| size_class | string | Size category |

## Common Analysis Patterns

### Comparing Sites
```python
# ANOVA for site comparison
from scipy import stats
sites = [group['coral_coverage_pct'].values for name, group in reef_data.groupby('site')]
f_stat, p_value = stats.f_oneway(*sites)
print(f"ANOVA: F={f_stat:.2f}, p={p_value:.4f}")
```

### Trend Analysis
```python
# Linear regression for temporal trends
from scipy.stats import linregress
dates = pd.to_datetime(reef_data['date']).astype(int) / 10**9
slope, intercept, r, p, se = linregress(dates, reef_data['coral_coverage_pct'])
print(f"Trend: {slope*365*24*3600:.2f}% per year (p={p:.4f})")
```

### Correlation Analysis
```python
# Environmental correlations
correlations = reef_data[['coral_coverage_pct', 'temperature', 'turbidity', 'depth_m']].corr()
sns.heatmap(correlations, annot=True, cmap='coolwarm')
plt.title('Environmental Correlations')
```

## Scripts Reference

### `scripts/download_reef_data.sh`
Downloads sample reef monitoring data for practice.

```bash
./scripts/download_reef_data.sh          # Download sample datasets
./scripts/download_reef_data.sh --region caribbean  # Regional data
```

### `scripts/validate_data.sh`
Validates reef survey data format.

```bash
./scripts/validate_data.sh data.csv      # Check data structure
```

## References

Load these reference documents for detailed guidance:

- **`references/metrics_guide.md`** - Detailed ecological metric calculations
- **`references/visualization_templates.md`** - Plot templates and styling
- **`references/report_templates.md`** - Report structure examples

## Success Criteria

A successful reef ecology report includes:
- [ ] Data loaded and validated
- [ ] Key metrics calculated (coverage, diversity, richness)
- [ ] At least 3 visualizations created
- [ ] Summary statistics compiled
- [ ] Report exported in requested format
- [ ] All figures saved at publication quality (300 dpi)
