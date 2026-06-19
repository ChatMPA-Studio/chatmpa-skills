#!/usr/bin/env bash
#
# validate_data.sh — Validate a reef-monitoring CSV file.
#
# Checks that the file exists and is non-empty, prints the column headers and
# row count, and warns if expected reef-survey columns are missing.
#
# Usage:
#   ./scripts/validate_data.sh data.csv

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: validate_data.sh <data.csv>

Validates a reef-monitoring CSV file:
  - checks the file exists and is non-empty
  - prints the column headers and data row count
  - warns if expected columns are missing
EOF
}

# --- argument handling ------------------------------------------------------
if [[ $# -ne 1 ]]; then
    usage >&2
    exit 1
fi

case "$1" in
    -h|--help)
        usage
        exit 0
        ;;
esac

CSV="$1"

# --- existence / non-empty checks -------------------------------------------
if [[ ! -f "$CSV" ]]; then
    echo "ERROR: file not found: $CSV" >&2
    exit 1
fi

if [[ ! -s "$CSV" ]]; then
    echo "ERROR: file is empty: $CSV" >&2
    exit 1
fi

# --- expected reef-survey columns -------------------------------------------
EXPECTED_COLUMNS=(site_id transect_id date depth_m hard_coral total_points)

echo "Validating: $CSV"
echo "----------------------------------------"

# Read the header (first line), stripping a trailing CR if present (CRLF files).
header="$(head -n 1 "$CSV" | tr -d '\r')"

if [[ -z "$header" ]]; then
    echo "ERROR: no header row found in $CSV" >&2
    exit 1
fi

# --- print headers ----------------------------------------------------------
echo "Column headers:"
# Split the header on commas and print one column per line, numbered.
IFS=',' read -r -a cols <<< "$header"
for i in "${!cols[@]}"; do
    printf '  %2d. %s\n' "$((i + 1))" "${cols[$i]}"
done
echo "Column count: ${#cols[@]}"

# --- count data rows (excludes header) --------------------------------------
total_lines="$(wc -l < "$CSV" | tr -d '[:space:]')"
# wc counts newlines; if the file lacks a trailing newline the last row is
# uncounted, so detect that and add one.
if [[ -n "$(tail -c 1 "$CSV")" ]]; then
    total_lines="$((total_lines + 1))"
fi
data_rows="$((total_lines - 1))"
echo "Data rows (excluding header): $data_rows"

if [[ "$data_rows" -le 0 ]]; then
    echo "WARNING: file has a header but no data rows." >&2
fi

# --- warn on missing expected columns ---------------------------------------
echo "----------------------------------------"
missing=()
for expected in "${EXPECTED_COLUMNS[@]}"; do
    found=0
    for col in "${cols[@]}"; do
        # trim leading/trailing whitespace from the column name
        trimmed="${col#"${col%%[![:space:]]*}"}"
        trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
        if [[ "$trimmed" == "$expected" ]]; then
            found=1
            break
        fi
    done
    if [[ "$found" -eq 0 ]]; then
        missing+=("$expected")
    fi
done

if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "WARNING: expected columns missing: ${missing[*]}" >&2
else
    echo "OK: all expected columns present."
fi

echo "----------------------------------------"
echo "Validation complete."
