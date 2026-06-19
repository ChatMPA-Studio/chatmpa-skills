# SDM Algorithm Comparison

## Introduction

Species distribution models (SDMs) relate species occurrence records to environmental
predictors to estimate habitat suitability across space. No single algorithm is best for
every problem; the right choice depends on the data type (presence-only vs.
presence-absence), sample size, and whether interpretability or predictive performance
matters most. This guide compares the algorithms most used for marine SDMs and the
conventions for evaluating them.

## Data Types

### Presence-only

Most marine biodiversity data (OBIS, GBIF) are presence-only: where the species was
recorded, but not where it was confirmed absent. These require a comparison set of
**background** or **pseudo-absence** points to characterize the available environment.

### Presence-absence

Surveys with a structured sampling design (e.g., LTEM transects, trawl surveys) yield
true absences. These support a wider range of algorithms and generally give less biased
estimates of prevalence.

### Background vs. pseudo-absence

| Concept | Meaning | Typical use |
|---------|---------|-------------|
| Background | Random sample of the study-area environment (not assumed absent) | MaxEnt, Poisson point-process models |
| Pseudo-absence | Points treated as absences for presence-absence algorithms | GLM, GAM, RF, BRT when no true absences exist |

Practical guidance:
- Draw background/pseudo-absence points from the same area and accessible range as the
  presences to avoid contrast artifacts.
- A common default is ~10,000 background points for MaxEnt; for machine-learning
  classifiers, ~1–10x the number of presences is typical (balance affects predicted
  prevalence).
- Apply an ocean mask so points fall in valid marine habitat, and consider restricting by
  depth or a target-group background to mirror sampling bias.

## Algorithms

### MaxEnt (maximum entropy)

Presence-background method that fits the distribution of maximum entropy subject to
constraints from environmental features. Widely used because it performs well with small
samples and only needs presence data.

- Strengths: strong with few records; built-in regularization; handles complex responses
  via feature classes; widely benchmarked.
- Weaknesses: sensitive to background choice and sampling bias; outputs are relative
  suitability, not probability of occurrence; tuning (regularization multiplier, feature
  classes) matters.
- Tools: `maxnet`/`dismo` (R), the original Java MaxEnt, `elapid` (Python).

### GLM (generalized linear model)

Regression (typically logistic) of presence-absence on predictors. The transparent
baseline for SDM.

- Strengths: interpretable coefficients; fast; well-understood statistics.
- Weaknesses: assumes the specified functional form (often linear or low-order
  polynomial); misses complex nonlinear responses and interactions unless added manually.

### GAM (generalized additive model)

Extends the GLM with smooth (spline) terms, capturing nonlinear environmental responses
while staying interpretable.

- Strengths: flexible nonlinear responses; smoothness controllable to limit overfitting;
  partial-response plots aid ecological interpretation.
- Weaknesses: can overfit with too many knots; interactions less natural than tree
  methods.

### Random forest (RF)

Ensemble of decision trees on bootstrap samples with random feature subsets; predictions
are averaged across trees.

- Strengths: captures nonlinearity and interactions automatically; robust to noise;
  variable-importance and partial-dependence diagnostics.
- Weaknesses: can overfit if presence-absence is strongly imbalanced; extrapolates poorly
  outside the training environment; less interpretable than GLM/GAM.
- Tools: `scikit-learn` `RandomForestClassifier`, R `randomForest`/`ranger`.

### BRT / GBM (boosted regression trees)

Boosting fits trees sequentially, each correcting the residuals of the previous, often the
top performer in SDM benchmarks.

- Strengths: high predictive accuracy; models interactions and nonlinearity; tunable
  (learning rate, tree complexity, number of trees).
- Weaknesses: more hyperparameters to tune; can overfit without a low learning rate and
  cross-validation; slower to train.
- Tools: `gbm`/`dismo` (R), `scikit-learn` `GradientBoostingClassifier`, XGBoost,
  LightGBM.

### Ensembles

Combine predictions from several algorithms (e.g., mean or weighted mean by evaluation
score) to reduce single-model bias and express uncertainty across methods.

- Strengths: often more robust and transferable than any single model; the spread across
  models is a useful uncertainty measure.
- Weaknesses: more computation; a poor member can degrade an unweighted mean; harder to
  interpret.
- Tools: the `biomod2` framework (R) automates multi-algorithm fitting and ensembles.

## Algorithm Summary

| Algorithm | Data type | Nonlinearity | Interpretability | Notes |
|-----------|-----------|--------------|------------------|-------|
| MaxEnt | Presence-background | High | Medium | Strong with few records |
| GLM | Presence-absence | Low | High | Transparent baseline |
| GAM | Presence-absence | Medium-high | High | Smooth response curves |
| Random forest | Presence-absence | High | Medium | Robust; weak extrapolation |
| BRT/GBM | Presence-absence | High | Medium | Often best accuracy; needs tuning |
| Ensemble | Any | Varies | Low | Combines models, quantifies spread |

## Evaluation

### Metrics

| Metric | Range | Interpretation |
|--------|-------|----------------|
| AUC (ROC) | 0.5–1.0 | Threshold-independent discrimination; 0.5 = random |
| TSS | -1 to 1 | Sensitivity + specificity − 1; threshold-dependent |
| Sensitivity | 0–1 | Proportion of presences correctly predicted |
| Specificity | 0–1 | Proportion of absences/background correctly predicted |
| Boyce index | -1 to 1 | Presence-only metric of predicted-to-expected ratio |

AUC rough guide: 0.7–0.8 fair, 0.8–0.9 good, >0.9 excellent. For presence-only models AUC
is capped below 1 and is best read as a relative comparison among models on the same data.
TSS is a common threshold-dependent alternative; the Boyce index is preferred when only
presences are available.

### Cross-validation

- **Random k-fold** (e.g., 5- or 10-fold) is the default but inflates scores under spatial
  autocorrelation because nearby train/test points are not independent.
- **Spatial / block cross-validation** assigns spatially contiguous blocks to folds, giving
  a more honest estimate of transferability. Tools: `blockCV` (R), `spacv` (Python).
- Reserve a fully independent dataset (different time period or region) for final
  evaluation when available.

## Practical Recommendations

1. Match the algorithm to the data: presence-only → MaxEnt or a point-process model;
   presence-absence → GLM/GAM (interpretation) or RF/BRT (accuracy).
2. Standardize background/pseudo-absence sampling and mirror known sampling bias.
3. Use spatial cross-validation to avoid optimistic AUC/TSS from autocorrelation.
4. Report at least two metrics (e.g., AUC and TSS, plus Boyce for presence-only).
5. Consider an ensemble to bracket prediction uncertainty rather than trusting one model.
6. Inspect response curves and variable importance for ecological plausibility, not just
   scores.
