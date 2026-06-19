# Marine Biodiversity Gradients

This reference explains the **latitudinal diversity gradient (LDG)** and its
leading hypothesised drivers, then connects them to the biogeography of Baja
California and the Gulf of California so the LTEM latitudinal-gradient step can be
interpreted correctly. It is conceptual; it contains no dataset values.

## The Latitudinal Diversity Gradient

The latitudinal diversity gradient is one of the most general patterns in
ecology: **species richness tends to be highest near the tropics and to decline
toward the poles.** It holds across most marine taxa, including reef fishes.

Two clarifications matter for LTEM work:

1. **Richness and biomass are not the same axis.** The LDG concerns *number of
   species*. Total *biomass* and *productivity* follow their own logic and can
   peak at different latitudes (often where upwelling and bottom-up energy are
   high — see `environmental_drivers.md`). Do not assume the most species-rich
   region is the most biomass-rich.

2. **The pattern can be noisy or reversed over short, regionally complex
   gradients.** Baja California spans a relatively narrow latitudinal band with
   strong local oceanography, so a clean monotonic LDG is not guaranteed; local
   drivers can dominate.

## Leading Hypotheses for the Gradient

No single mechanism fully explains the LDG; several reinforce one another.

| Hypothesis | Core idea |
|------------|-----------|
| Energy / productivity | More available energy (warmth, primary production) supports more individuals and more coexisting species |
| Thermal / kinetic | Higher temperature speeds metabolism, growth, and possibly diversification rates |
| Time and area | Tropical regions are large and have been climatically stable over long periods, allowing more speciation and less extinction |
| Climatic stability | Stable conditions favour specialization and narrow niches, packing more species |
| Niche / biotic interactions | Stronger biotic interactions in the tropics promote specialization and coexistence |

For interpreting LTEM correlations, the **energy** and **thermal** hypotheses are
the most directly testable, because SST and chlorophyll are measured variables.
A positive richness–SST correlation is consistent with the thermal/energy
mechanisms operating across the sampled gradient.

## Biogeography of Baja California and the Gulf of California

The southern Baja California peninsula and Gulf of California sit at a
**temperate–tropical transition (an ecotone)**. This makes the region unusually
informative — and unusually complex — for gradient analysis.

### Faunal provinces and the transition

- The **outer Pacific coast of Baja** trends from cool-temperate in the north
  toward warmer conditions in the south.
- The **Gulf of California (Sea of Cortez)** has a strong internal gradient: the
  **Upper Gulf / Alto Golfo** is cooler, more seasonally variable, more
  productive and turbid, while the **southern Gulf and Cape region** are warmer
  and more tropical.
- The Cape region acts as a **biogeographic boundary** where temperate and
  tropical (including tropical Eastern Pacific) faunas overlap, producing a mix
  of warm- and cool-affiliated species.

Because of this overlap, southern Gulf reefs often combine high richness (tropical
affinities) with the strong seasonal/upwelling productivity of a temperate-influenced
sea.

### Oceanographic drivers that complicate a simple LDG

- **Upwelling and seasonality.** Wind- and tide-driven upwelling injects
  nutrients, raising chlorophyll and supporting high biomass independent of the
  richness gradient. Productive cool-water zones can hold high biomass with
  moderate richness.
- **Endemism.** The Gulf of California has notable endemism (species restricted to
  the Gulf), so local richness reflects evolutionary history, not just
  present-day temperature.
- **Strong thermal seasonality.** The Gulf experiences large seasonal SST swings;
  annual-mean SST can mask the seasonal extremes that actually shape
  distributions.
- **Confounding with depth, habitat, and protection.** Within the LTEM design,
  latitude co-varies with reef structure, depth strata, and protection status
  (e.g. Cabo Pulmo). A raw latitude correlation can partly reflect these.

## How This Maps onto the LTEM Latitudinal Step

The workflow bins surveys by latitude and correlates latitude with biomass,
richness, productivity, SST, and chlorophyll. Interpret as follows:

| Observation | Plausible reading |
|-------------|-------------------|
| Richness rises toward the warm (southern/tropical) end | Consistent with the classic LDG and thermal/energy hypotheses |
| Biomass peaks where chlorophyll/upwelling is high, not where richness peaks | Bottom-up energy control decoupled from the diversity gradient |
| Latitude correlates with SST and chlorophyll | Latitude is a *proxy* for the underlying climate gradient, not a driver itself |
| Gradient weak or non-monotonic | Expected — local oceanography and a narrow latitudinal span can override the global LDG |

**Key interpretive rule:** latitude is a stand-in for the environmental gradient
(temperature, productivity, seasonality, biogeographic history). Where SST and
chlorophyll are available, attribute patterns to those measured drivers rather
than to latitude per se, and remember that biogeographic history (endemism,
province boundaries) contributes to richness in ways no environmental covariate
captures.

## Statistical Cautions

- Latitude is strongly collinear with SST and chlorophyll; do not treat a
  latitude effect and a temperature effect as independent without a multivariate
  model.
- Binning by whole degrees of latitude trades resolution for stable group sizes;
  report the number of surveys per bin so sparse bins are not over-interpreted.
- Use rank-based (Spearman) correlations for these typically non-linear gradients,
  consistent with the rest of the workflow.
- A gradient in a single regional dataset is one realization of a global pattern;
  frame conclusions regionally and avoid over-generalizing.
