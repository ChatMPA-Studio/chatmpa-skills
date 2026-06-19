# WDPA Data Field Descriptions

The **World Database on Protected Areas (WDPA)** is the global reference
dataset of protected and conserved areas, compiled by UNEP-WCMC and IUCN and
distributed through **Protected Planet** (https://www.protectedplanet.net).
It is supplied as polygon (and point) layers in shapefile / file-geodatabase /
GeoJSON form. The attribute schema is publicly documented and stable; the
fields below are the standard WDPA attributes most relevant to MPA analysis.

## Standard Attribute Fields

| Field | Type | Description | Use in MPA analysis |
|-------|------|-------------|---------------------|
| `WDPAID` | numeric | Unique numeric identifier for the protected area | Primary key; join, dedupe, reference across versions |
| `WDPA_PID` | text | Unique identifier for each parcel of a protected area | Distinguish multiple polygons of one PA |
| `NAME` | text | Protected area name (local/official) | Labelling, reporting |
| `ORIG_NAME` | text | Original name in the original language | Cross-referencing local records |
| `DESIG` | text | Designation name (original language) | Identify designation type |
| `DESIG_ENG` | text | Designation in English | Filter/group by designation type |
| `DESIG_TYPE` | text | Designation type: National / International / Regional / Not Applicable | Separate national vs international instruments |
| `IUCN_CAT` | text | IUCN protected-area management category (Ia, Ib, II, III, IV, V, VI, plus "Not Reported / Not Applicable / Not Assigned") | Proxy for protection strictness; stratify analyses |
| `INT_CRIT` | text | International criteria (for internationally designated sites) | Context for international designations |
| `MARINE` | text | Marine flag: 0 = terrestrial, 1 = coastal (mix of land & sea), 2 = marine | Select marine/coastal PAs |
| `REP_M_AREA` | numeric | Reported marine area (km²) | Marine extent as reported |
| `GIS_M_AREA` | numeric | Marine area computed from GIS geometry (km²) | Cross-check reported marine area |
| `REP_AREA` | numeric | Reported total area (km²) | Reported size; compare to GIS area |
| `GIS_AREA` | numeric | Total area computed from the GIS geometry (km²) | Authoritative area for spatial calcs |
| `NO_TAKE` | text | No-take status: All / Part / None / Not Reported / Not Applicable | Identify fully vs partially no-take MPAs |
| `NO_TK_AREA` | numeric | Area of the no-take zone (km²) | Quantify strictly protected extent |
| `STATUS` | text | Legal status: Designated / Inscribed / Adopted / Proposed / Established | Filter to in-force PAs |
| `STATUS_YR` | numeric | Year the current status took effect | Time-since-protection; BACI before/after split |
| `GOV_TYPE` | text | Governance type (e.g. federal, sub-national, NGO, community, co-managed) | Governance context |
| `OWN_TYPE` | text | Ownership type | Ownership context |
| `MANG_AUTH` | text | Management authority | Attribution, enforcement context |
| `MANG_PLAN` | text | Reference to a management plan | Management capacity indicator |
| `VERIF` | text | Verification state (State Verified / Expert Verified / Not Reported) | Data-quality screening |
| `METADATAID` | numeric | Link to the source-metadata record | Provenance / source lookup |
| `SUB_LOC` | text | Sub-national location code (ISO 3166-2) | Sub-national filtering |
| `PARENT_ISO3` | text | ISO3 code of the parent country | Country-level grouping |
| `ISO3` | text | ISO3 country code(s) of the PA | Country selection / joins |

## Practical Filtering

Selecting marine protected areas and in-force sites:

```python
import geopandas as gpd

wdpa = gpd.read_file("WDPA_polygons.shp")

# Marine and coastal PAs only (MARINE is stored as text "1"/"2")
marine = wdpa[wdpa["MARINE"].isin(["1", "2"])]

# In-force designations
marine = marine[marine["STATUS"].isin(["Designated", "Inscribed", "Established"])]

# Strictly protected (no-take) subset
no_take = marine[marine["NO_TAKE"].isin(["All", "Part"])]
```

## Notes and Caveats

- `MARINE` and several status/category fields are stored as **text** in many
  WDPA distributions; cast or compare as strings.
- Prefer `GIS_AREA` / `GIS_M_AREA` for spatial computation; `REP_AREA` /
  `REP_M_AREA` are self-reported and can diverge from the geometry.
- `IUCN_CAT` is a *management* category, not an enforcement measure — many PAs
  are "Not Reported"; do not equate a category with realized protection.
- Some PAs are represented only as **points** (no polygon); the WDPA point
  layer carries the same attribute schema but cannot be used for area-based
  spatial joins.
- Always cite the WDPA version/month and the UNEP-WCMC & IUCN conditions of use
  when reporting (see Protected Planet for the current citation).
