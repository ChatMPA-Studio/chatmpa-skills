# conapesca-lfo-ca — Analysis Notes

**Run date:** 2026-08-04  
**Run by:** Eduardo (via Claude Code session)  
**Data:** `conapesca_landings_2001_2026_2026-07-15.rds` (local copy, gitignored)

---

## What this analysis does

Groups Mexico's fishing landing offices (LFOs) into fishing regions based on catch composition similarity (Correspondence Analysis, following Erisman et al. 2011). The output is a lookup table `office name → region_id` used to assign coastal MPAs to a fishing context for the chatMPA demo.

---

## Key methodological decisions made

### 1. Fleet filter: MENORES only
- **Decision:** Run on `tipo_aviso == "MENORES"` (artisanal fleet) only — exclude MAYORES.
- **Why:** Industrial ports (Guaymas, Mazatlán, Manzanillo) are dominated by shrimp/tuna and distort the composition signal. Artisanal fishing pressure is what matters for MPA management context.

### 2. Coastal offices only (those with coordinates)
- **Decision:** Restrict to the 81 offices that have lat/lon in the raw data.
- **Why:** Inland/freshwater offices (Guadalajara, Pátzcuaro, Ciudad Acuña…) have no spatial relationship to marine MPAs and inflate the CA space. Also enables geographic-constraint clustering.
- **Gap:** Gulf of Mexico (Veracruz, Tamaulipas, Campeche) and Caribbean (Cancún, Cozumel) offices lack coordinates in the current dataset — they are excluded. These regions exist but have no entries in the lookup table.

### 3. Geographic-constraint clustering
- **Decision:** Run k-means on **CA1 + CA2 + scaled_lat + scaled_lon** (all 4 dimensions scaled to mean=0, sd=1).
- **Why:** Pure CA clustering groups offices by catch composition regardless of location — this produced geographically incoherent clusters (e.g., Pacific Oaxaca mixed with Gulf of California). Adding lat/lon as equal-weight dimensions forces nearby offices to stay together while still respecting composition similarity.

### 4. Year range: 2001–2026
- **Decision:** Use full database range rather than the 2001–2010 default in skill.R.
- **Why:** More years → more stable mean catch composition per office. The geographic structure was confirmed stable across both windows (2001–2010 vs. 2001–2026 gave the same regional clusters). Spatial correlation with lat/lon slightly stronger in the longer window.

---

## Results summary

**Dataset after filters:** 5,685,636 rows | 81 coastal offices | 1,352 species  
**MLG (DCA axis 1 range):** 6.68 SD → CA confirmed (threshold = 3.0)  
**CA2 vs. latitude:** r = −0.26, p = 0.019  
**CA2 vs. longitude:** r = +0.19, p = 0.09  

### WK/KL indices

| k | WK | KL |
|---|---|---|
| 3 | 101.2 | 6.03 |
| 4 | 78.1 | 0.34 |
| **5** | **57.3** | **50.83 ← statistical optimum** |
| 6 | 47.7 | 0.12 |
| **7** | **40.3** | **1.81 ← recommended** |
| 8 | 35.5 | 1.63 |
| 9 | 31.7 | 0.18 |
| 12 | 21.4 | 4.23 |

### Chosen k: **7**

k=5 is the statistical optimum but lumps BCS/Southern GoC with Pacific Baja Norte into one large region. k=7 cleanly separates all geographically meaningful zones.

### k=7 cluster assignments (geo-constrained, MENORES, coastal)

| region_id | n offices | Geographic identity | MPA relevance |
|---|---|---|---|
| 1 | 9 | **Inland freshwater** — Guadalajara, Chapala, Pátzcuaro, Cuitzeo, Zitácuaro | Exclude from MPA analysis |
| 2 | 13 | **Pacific Baja Norte** — Tijuana, Ensenada, San Quintín, Guerrero Negro, Isla Cedros, Bahía Tortugas, Santa Rosalía, Punta Abreojos | Baja Norte Pacific MPAs |
| 3 | 10 | **Central Pacific + inland** — Tepic, Colima, Acapulco, Oaxaca, Tuxtla Gutiérrez | Guerrero/Oaxaca coast MPAs |
| 4 | 16 | **Nayarit → Guerrero mainland coast** — Mazatlán, Escuinapa, San Blas, Puerto Vallarta, Manzanillo, Lázaro Cárdenas, Zihuatanejo | Nayarit/Jalisco/Michoacán MPAs |
| 5 | 14 | **Southern Gulf of California + BCS** — Loreto, La Paz, Cabo San Lucas, Los Mochis, Topolobampo, San Carlos | **Main MPA corridor (Cabo Pulmo, Loreto, APFF BCS)** |
| 6 | 8 | **Northern Gulf of California** — Mexicali, Golfo de Santa Clara, San Felipe, Guaymas, Cd. Obregón | Alto Golfo, Sonora coast |
| 7 | 11 | **Oaxaca/Chiapas coast** — Salina Cruz, Puerto Escondido, Puerto Ángel, Puerto Madero | Southern Pacific MPAs |

Full office-level lookup: `references/lfo_region_lookup_k9.csv` (generated from earlier k=9 run — **needs to be regenerated for k=7 with geo-constraint**).

---

## Pending before committing lookup table

1. **Regenerate lookup as k=7 geo-constrained** — the file currently in `references/` is from the unconstrained k=9 run. Eduardo confirmed k=7 geo-constrained is the right approach; file needs to be re-saved with the correct cluster assignments.
2. **Carolina/Fabio sign-off** on region definitions — especially whether region 1 (inland freshwater) should be dropped entirely from the lookup or kept with a flag.
3. **Add Gulf of Mexico + Caribbean** — 25+ offices lack coordinates. Options: (a) manually assign coordinates from public SAGARPA/CONAPESCA office address data, (b) assign them to the nearest coastal region by geographic proximity after the fact.
4. **Update `setup_grid_attributes.R`** to stamp `region_id` onto grid cells using the final lookup table.

---

## Scripts used

- `shared/local_loader/local_loader.R` — loads local RDS copy, applies MENORES filter
- `per-database/conapesca-lfo-ca/skill.R` — CA ordination (called via `run_skill()`)
- Geo-constrained clustering was done in a scratch script (not yet a formal skill) — see session notes or re-derive from this document + `run_skill()` output + the k-means block in `conapesca-lfo-regions/skill.R`
