# Report Structure Examples

Recommended structure for a reef ecology report produced in chatMPA Studio. Use the
skeletons below as starting points and drop in calculated metrics and saved figures.
A typical report flows: **Summary -> Methods -> Results -> Figures -> Interpretation ->
Recommendations**.

## Recommended Section Structure

| Section            | Purpose                                                      |
|--------------------|-------------------------------------------------------------|
| Title & metadata   | Site, survey dates, authors, methodology name               |
| Executive summary  | 3-5 bullet headline findings for non-specialist readers     |
| Introduction       | Context, objectives, study question                         |
| Methods            | Survey design, sampling, metrics, software                  |
| Results            | Metric values, tables, statistical tests                    |
| Figures            | Referenced visualizations with captions                     |
| Interpretation     | What the results mean for reef health                       |
| Recommendations    | Management or monitoring actions                             |
| Limitations        | Caveats, data gaps, assumptions                             |
| References         | Methods and prior studies                                   |

## Full Report Skeleton

```markdown
# Reef Ecology Survey Report - <Site / Region>

**Survey period:** <start date> - <end date>
**Sites surveyed:** <n>   **Transects:** <n>   **Method:** <e.g., point-intercept transect>
**Prepared by:** <author>   **Date:** <report date>

---

## Executive Summary

- Mean hard coral cover across sites was **<x>%** (range <min>-<max>%).
- Community diversity (Shannon H') averaged **<x>**, indicating <low/medium/high> diversity.
- Bleaching prevalence was **<x>%**, with severity index **<x>/4**.
- <One sentence on overall reef condition and trend.>

## 1. Introduction

Briefly state the monitoring objective and the question this survey answers
(e.g., baseline assessment, post-disturbance recovery, MPA effectiveness).

## 2. Methods

- **Study area:** sites, coordinates, depth range.
- **Survey design:** transect length/number, quadrat or point-intercept spacing.
- **Benthic categories:** hard coral, soft coral, macroalgae, turf, CCA, rubble, sand, other.
- **Metrics:** percent cover, species richness (S), Shannon H', Simpson D, Pielou J',
  bleaching prevalence and severity index.
- **Analysis:** software (Python: pandas, numpy, scipy, matplotlib/seaborn); statistical
  tests used (e.g., one-way ANOVA for among-site comparison).

## 3. Results

### 3.1 Coral Cover

| Site | Mean cover (%) | SD | n transects |
|------|----------------|----|-------------|
| ...  | ...            | .. | ...         |

### 3.2 Diversity

| Site | Richness (S) | Shannon (H') | Simpson (D) | Evenness (J') |
|------|--------------|--------------|-------------|---------------|
| ...  | ...          | ...          | ...         | ...           |

### 3.3 Bleaching

| Site | Prevalence (%) | Severity index (0-4) |
|------|----------------|----------------------|
| ...  | ...            | ...                  |

### 3.4 Statistical Comparison

State test, statistic, and p-value, e.g.:
`Among-site difference in coral cover: ANOVA F = <x>, p = <x>.`

## 4. Figures

![Mean coral cover by site](cover_by_site.png)
*Figure 1. Mean hard coral cover by survey site; dashed line shows the overall mean.*

![Benthic composition](benthic_composition.png)
*Figure 2. Benthic community composition by site.*

![Diversity by site](diversity_by_site.png)
*Figure 3. Shannon diversity (H') by site with replicate standard deviation.*

![Coral cover trend](cover_timeseries.png)
*Figure 4. Temporal trend in hard coral cover.*

![Bleaching severity](bleaching_severity.png)
*Figure 5. Distribution of bleaching severity classes by site.*

## 5. Interpretation

Relate metrics to reef condition: how does coral cover compare to regional baselines,
does the algae-to-coral balance suggest a phase shift, and what does the bleaching index
imply about recent thermal stress? Note spatial patterns among sites.

## 6. Recommendations

- Monitoring cadence and priority sites.
- Management actions (e.g., reduce local stressors at high-algae sites).
- Data or sampling improvements for the next survey.

## 7. Limitations

Sampling effort, single-season snapshot, observer variability, taxonomic resolution.

## References

List methods sources (e.g., point-intercept transect and AGRRA protocols) and any
prior monitoring reports for the site.
```

## Short / Rapid-Assessment Skeleton

For quick field summaries, collapse to four sections.

```markdown
# Rapid Reef Assessment - <Site>

**Date:** <date>   **Method:** <method>   **Transects:** <n>

## Key Findings
- Coral cover: <x>%  |  Shannon H': <x>  |  Bleaching: <x>%

## Snapshot
![Coral cover by site](cover_by_site.png)

## Condition
<2-3 sentences interpreting reef health.>

## Next Steps
- <action 1>
- <action 2>
```

## Tips

- Keep one figure per finding; reference every figure by number in the text.
- Put exact metric values in tables, not prose, so they are easy to scan and update.
- Write the executive summary last, after the results are final.
- State the survey method and date prominently - reef metrics are only comparable within
  the same methodology.
