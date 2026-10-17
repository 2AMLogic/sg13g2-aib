# Source me:  source sim/harness/env.sh
#
# Resolves PDK_ROOT/PDK for the vendored sim/harness/common/build-osdi.sh
# (which sources ../env.sh relative to itself) and for the testbenches.
# Order: an explicit PDK_ROOT, then the repo-local install made by
# sim/harness/common/fetch-pdk.sh (sim/build/pdk), then the usual prefixes.
# shellcheck shell=bash
_aib_env_self="${BASH_SOURCE[0]}"
_aib_harness_dir="$(cd "$(dirname "${_aib_env_self}")" && pwd)"
_aib_sim_dir="$(cd "${_aib_harness_dir}/.." && pwd)"

export PDK="${PDK:-ihp-sg13g2}"

if [[ -z "${PDK_ROOT:-}" ]]; then
  for _aib_candidate in "${_aib_sim_dir}/build/pdk" /usr/share/pdk /usr/local/share/pdk \
                        "${HOME}/share/pdk" "${HOME}/.ciel" "${HOME}/.volare"; do
    if [[ -d "${_aib_candidate}/${PDK}/libs.tech/ngspice" ]]; then
      export PDK_ROOT="${_aib_candidate}"
      break
    fi
  done
fi

if [[ -n "${PDK_ROOT:-}" && -d "${PDK_ROOT}/${PDK}/libs.tech/ngspice" ]]; then
  export AIB_OSDI_DIR="${PDK_ROOT}/${PDK}/libs.tech/ngspice/osdi"
  echo "aib-sim: PDK_ROOT=${PDK_ROOT} PDK=${PDK}"
else
  echo "aib-sim: no ${PDK} install found; run sim/harness/common/fetch-pdk.sh (pin: sim/pdk.json)" >&2
fi
unset _aib_env_self _aib_harness_dir _aib_sim_dir _aib_candidate
