# Plot Templates and Styling

Runnable matplotlib/seaborn templates for reef monitoring figures. All snippets assume `pandas`, `numpy`, `matplotlib.pyplot as plt`, and `seaborn as sns` are imported and that metrics (percent cover, diversity indices, bleaching index) have already been calculated.

## Consistent Styling

Apply one global style block at the top of any reporting script so every figure shares the same fonts, grid, and resolution.

``` python
import matplotlib.pyplot as plt
import seaborn as sns

def set_reef_style():
    """Apply a consistent chatMPA reef-report style."""
    sns.set_theme(style='whitegrid', context='notebook')
    plt.rcParams.update({
        'figure.figsize': (10, 6),
        'figure.dpi': 110,          # screen preview
        'savefig.dpi': 300,         # publication export
        'savefig.bbox': 'tight',
        'font.size': 11,
        'axes.titlesize': 14,
        'axes.titleweight': 'bold',
        'axes.labelsize': 12,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'legend.frameon': False,
    })

set_reef_style()
```

## Color Guidance

Use a small, fixed palette so categories stay consistent across every figure in a report.

``` python
# Sequential ocean palette for continuous values / single-series plots
OCEAN = ['#023E8A', '#0077B6', '#00B4D8', '#90E0EF', '#CAF0F8']

# Categorical palette for benthic categories (keep mapping stable across figures)
BENTHIC_COLORS = {
    'Hard Coral':   '#E76F51',  # warm = living coral
    'Soft Coral':   '#F4A261',
    'Macroalgae':   '#2A9D8F',  # green for algae
    'Turf Algae':   '#8AB17D',
    'CCA':          '#E9C46A',  # crustose coralline algae
    'Rubble':       '#BDBDBD',
    'Sand':         '#E0D8C3',
    'Other':        '#6C757D',
}

# Bleaching severity ramp (0 = healthy, 4 = recently dead)
BLEACHING_COLORS = ['#118AB2', '#F2E8CF', '#FFD166', '#EF8354', '#9D0208']
```

Color tips: - Reserve red/orange hues for living coral and severe bleaching so warm = "biologically active or stressed"; use cool blues for healthy baselines. - Keep one color per benthic category for the whole report — never let "Hard Coral" change color between figures. - Check palettes for color-blind safety (seaborn's `colorblind` palette is a safe fallback).

## 1. Coral Cover Bar Chart (by site)

``` python
def plot_cover_by_site(df, site_col='site_id', cover_col='coral_coverage_pct'):
    means = df.groupby(site_col)[cover_col].mean().sort_values(ascending=False)
    fig, ax = plt.subplots()
    means.plot(kind='bar', color=OCEAN[1], ax=ax)
    ax.set_xlabel('Survey Site')
    ax.set_ylabel('Mean Hard Coral Cover (%)')
    ax.set_title('Mean Hard Coral Cover by Site')
    ax.axhline(means.mean(), ls='--', lw=1, color='grey',
               label=f'Overall mean ({means.mean():.1f}%)')
    ax.legend()
    fig.tight_layout()
    fig.savefig('cover_by_site.png')
    return fig
```

## 2. Stacked Benthic Composition

Show how the benthos partitions into categories per site. Expects a wide table with one column per benthic category (values as percentages summing to \~100).

``` python
def plot_benthic_stack(df_wide, site_col='site_id'):
    cats = [c for c in BENTHIC_COLORS if c in df_wide.columns]
    colors = [BENTHIC_COLORS[c] for c in cats]
    ax = df_wide.set_index(site_col)[cats].plot(
        kind='bar', stacked=True, color=colors, figsize=(11, 6))
    ax.set_xlabel('Survey Site')
    ax.set_ylabel('Cover (%)')
    ax.set_title('Benthic Community Composition by Site')
    ax.set_ylim(0, 100)
    ax.legend(title='Category', bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.figure.tight_layout()
    ax.figure.savefig('benthic_composition.png')
    return ax.figure
```

## 3. Diversity Comparison

Plot a diversity index (Shannon H', Simpson D, or richness S) across sites with optional error bars from replicate transects.

``` python
def plot_diversity(df, site_col='site_id', metric_col='shannon_H'):
    grp = df.groupby(site_col)[metric_col]
    means, errs = grp.mean(), grp.std()
    fig, ax = plt.subplots()
    means.plot(kind='bar', yerr=errs, capsize=4, color=OCEAN[0], ax=ax)
    ax.set_xlabel('Survey Site')
    ax.set_ylabel("Shannon Diversity (H')")
    ax.set_title('Coral Community Diversity by Site')
    fig.tight_layout()
    fig.savefig('diversity_by_site.png')
    return fig
```

## 4. Time Series of Reef Health

Track a metric through time, optionally split by site. Parse dates first so the x-axis is ordered correctly.

``` python
def plot_cover_timeseries(df, date_col='date', cover_col='coral_coverage_pct',
                          site_col='site_id'):
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    fig, ax = plt.subplots()
    for i, (site, sub) in enumerate(df.groupby(site_col)):
        ts = sub.groupby(date_col)[cover_col].mean()
        ts.plot(ax=ax, marker='o', label=site, color=OCEAN[i % len(OCEAN)])
    ax.set_xlabel('Survey Date')
    ax.set_ylabel('Hard Coral Cover (%)')
    ax.set_title('Temporal Trend in Coral Cover')
    ax.legend(title='Site')
    fig.tight_layout()
    fig.savefig('cover_timeseries.png')
    return fig
```

## 5. Bleaching Severity

A stacked horizontal bar showing the proportion of colonies in each bleaching class per site reads well in reports. Expects counts per class in wide form.

``` python
def plot_bleaching(df_wide, site_col='site_id',
                   classes=('Healthy', 'Pale', 'Partial', 'Severe', 'Dead')):
    prop = df_wide.set_index(site_col)[list(classes)]
    prop = prop.div(prop.sum(axis=1), axis=0) * 100   # row-normalize to %
    ax = prop.plot(kind='barh', stacked=True, color=BLEACHING_COLORS,
                   figsize=(10, 6))
    ax.set_xlabel('Colonies (%)')
    ax.set_ylabel('Survey Site')
    ax.set_title('Bleaching Severity Distribution by Site')
    ax.set_xlim(0, 100)
    ax.legend(title='Status', bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.figure.tight_layout()
    ax.figure.savefig('bleaching_severity.png')
    return ax.figure
```

## 6. Environmental Correlation Heatmap

``` python
def plot_correlations(df, cols):
    corr = df[cols].corr()
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm',
                center=0, vmin=-1, vmax=1, square=True, ax=ax)
    ax.set_title('Environmental Correlations')
    fig.tight_layout()
    fig.savefig('correlations.png')
    return fig
```

## Export Settings

| Use case            | Format  | DPI | Notes                            |
|---------------------|---------|-----|----------------------------------|
| Publication / print | PNG     | 300 | Default for the report; lossless |
| Vector / journals   | PDF/SVG | n/a | Scales without pixelation        |
| Web / slides        | PNG     | 150 | Smaller file, fine for screens   |

``` python
# Save the same figure in multiple formats
for ext in ('png', 'pdf'):
    fig.savefig(f'figure.{ext}', dpi=300, bbox_inches='tight')
plt.close(fig)   # free memory when generating many figures in a loop
```

Always close figures (`plt.close(fig)`) inside batch loops to avoid memory buildup, and keep `bbox_inches='tight'` so legends placed outside the axes are not clipped.