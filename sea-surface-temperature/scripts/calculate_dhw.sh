#!/usr/bin/env bash
#
# calculate_dhw.sh - Compute Degree Heating Weeks (DHW) from a NetCDF SST file.
#
# Implements the NOAA Coral Reef Watch standard:
#   HotSpot = max(SST - MMM, 0)
#   DHW     = (1/7) * rolling 84-day sum of HotSpots >= 1 degC   [degC-weeks]
#
# MMM (Maximum Monthly Mean) is derived from the input file's own monthly
# climatology (the warmest climatological month per grid cell). For operational
# work, supply an MMM consistent with the official CRW reference climatology.
#
# SST is auto-detected from common variable names and converted to degC if it
# appears to be in Kelvin (values > 100). The output NetCDF contains: sst_celsius,
# mmm, hotspot, dhw.
#
# Usage:
#   ./scripts/calculate_dhw.sh input.nc output_dhw.nc [sst_variable]
#
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: calculate_dhw.sh INPUT.nc OUTPUT_DHW.nc [SST_VARIABLE]

  INPUT.nc        NetCDF file containing a daily SST variable with a 'time' dim.
  OUTPUT_DHW.nc   Path for the output NetCDF (sst_celsius, mmm, hotspot, dhw).
  SST_VARIABLE    Optional. SST variable name. Auto-detected if omitted
                  (tries: analysed_sst, sst, sea_surface_temperature, SST).

Requires python3 with xarray and netcdf support (e.g. netCDF4).
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "Error: expected 2 or 3 arguments, got $#." >&2
    echo >&2
    usage >&2
    exit 1
fi

INPUT="$1"
OUTPUT="$2"
SST_VAR="${3:-}"

if [[ ! -f "$INPUT" ]]; then
    echo "Error: input file not found: $INPUT" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 not found on PATH." >&2
    exit 1
fi

python3 - "$INPUT" "$OUTPUT" "$SST_VAR" <<'PYEOF'
import sys
import numpy as np
import xarray as xr

input_path, output_path, sst_var = sys.argv[1], sys.argv[2], sys.argv[3]

ds = xr.open_dataset(input_path)

# --- Resolve the SST variable ---------------------------------------------
candidates = ["analysed_sst", "sst", "sea_surface_temperature", "SST"]
if sst_var:
    if sst_var not in ds:
        sys.exit(f"Error: variable '{sst_var}' not in file. "
                 f"Available: {list(ds.data_vars)}")
    name = sst_var
else:
    name = next((c for c in candidates if c in ds), None)
    if name is None:
        sys.exit(f"Error: could not auto-detect an SST variable. "
                 f"Available: {list(ds.data_vars)}. Pass it as the 3rd argument.")

if "time" not in ds[name].dims:
    sys.exit(f"Error: variable '{name}' has no 'time' dimension; cannot compute DHW.")

sst = ds[name]

# --- Convert Kelvin -> Celsius if needed ----------------------------------
if float(sst.max()) > 100:
    sst = sst - 273.15
sst = sst.rename("sst_celsius")

# --- MMM: warmest climatological month per cell ---------------------------
monthly_clim = sst.groupby("time.month").mean("time")
mmm = monthly_clim.max("month").rename("mmm")

# --- HotSpot = max(SST - MMM, 0) ------------------------------------------
hotspot = (sst - mmm).clip(min=0).rename("hotspot")

# --- DHW: (1/7) * rolling 84-day sum of HotSpots >= 1 degC -----------------
n = sst.sizes["time"]
window = min(84, n)
if n < 84:
    print(f"Warning: only {n} timesteps (< 84-day window); "
          f"using window={window}. Treat DHW as incomplete.", file=sys.stderr)

hs_significant = hotspot.where(hotspot >= 1, 0)
dhw = (hs_significant.rolling(time=window, center=False).sum() / 7.0).rename("dhw")

# --- Assemble and write ----------------------------------------------------
out = xr.Dataset(
    {"sst_celsius": sst, "mmm": mmm, "hotspot": hotspot, "dhw": dhw}
)
out["dhw"].attrs.update(units="degC-weeks",
                        long_name="Degree Heating Weeks")
out["hotspot"].attrs.update(units="degC", long_name="Thermal HotSpot")
out["mmm"].attrs.update(units="degC",
                        long_name="Maximum Monthly Mean climatology (from input)")
out.attrs["dhw_method"] = (
    "NOAA Coral Reef Watch: HotSpot=max(SST-MMM,0); "
    "DHW=(1/7)*rolling 84-day sum of HotSpots>=1degC. "
    "MMM derived from input monthly climatology."
)

out.to_netcdf(output_path)

dmax = float(out["dhw"].max(skipna=True))
print(f"Wrote {output_path} (SST var: {name}). Max DHW = {dmax:.2f} degC-weeks.")
PYEOF
