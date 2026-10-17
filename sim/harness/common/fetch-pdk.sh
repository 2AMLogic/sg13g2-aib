#!/usr/bin/env bash
# fetch-pdk.sh -- fetch the IHP-Open-PDK release pinned in sim/pdk.json into
# sim/build/pdk (gitignored), failing closed on a tarball checksum mismatch.
#
#   sim/harness/common/fetch-pdk.sh [--force]
#   export PDK_ROOT="$PWD/sim/build/pdk" PDK=ihp-sg13g2
set -euo pipefail

SIM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PIN="${SIM_DIR}/pdk.json"
DEST="${PDK_FETCH_DEST:-${SIM_DIR}/build/pdk}"
MARKER="${DEST}/.fetched-sha256"

pin() { python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "${PIN}" "$1"; }
URL="$(pin release_url)"
WANT="$(pin tarball_sha256)"

if [[ "${1:-}" != "--force" && -f "${MARKER}" && "$(cat "${MARKER}")" == "${WANT}" ]]; then
  echo "fetch-pdk.sh: $(pin release_tag) already present at ${DEST} (use --force to refetch)"
  exit 0
fi

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
echo "fetch-pdk.sh: downloading ${URL}"
curl -fsSL -o "${tmp}/pdk.tar.gz" "${URL}"
got="$(sha256sum "${tmp}/pdk.tar.gz" | awk '{print $1}')"
if [[ "${got}" != "${WANT}" ]]; then
  echo "fetch-pdk.sh: SHA256 MISMATCH" >&2
  echo "  expected ${WANT}" >&2
  echo "  got      ${got}" >&2
  exit 4
fi
mkdir -p "${tmp}/x"
tar -xzf "${tmp}/pdk.tar.gz" -C "${tmp}/x" --strip-components=1
rm -rf "${DEST}"
mkdir -p "$(dirname "${DEST}")"
mv "${tmp}/x" "${DEST}"
echo "${WANT}" > "${MARKER}"
echo "fetch-pdk.sh: sha256 ${got} OK; PDK_ROOT=${DEST} PDK=ihp-sg13g2"
