#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
image=${1:?Pass candidate image tag}
common=(--rm --cpus 2 --memory 5g --pids-limit 512 --user 99:100 --read-only
        --cap-drop ALL --security-opt no-new-privileges:true
        --tmpfs /tmp:size=1073741824,mode=1777 -e PYTHONDONTWRITEBYTECODE=1)
docker run "${common[@]}" --network none -e PYTHONPATH=/opt/papercut \
  -v "$PWD/tests:/checks:ro" \
  -v "$PWD/.build/source:/upstream:ro" \
  "$image" python /checks/check_requirements.py
docker run "${common[@]}" --network none -e PYTHONPATH=/opt/papercut \
  -v "$PWD/tests:/checks:ro" "$image" python /checks/test_reader_only.py
docker run "${common[@]}" -e HOME=/tmp -e PAPER_READER_LIBRARY=/tmp/unit-library \
  -e PAPERCUT_WORKER=0 -e PYTHONPATH=/tmp/test-deps:/opt/papercut \
  -v "$PWD/.build/source/tests:/checks/upstream:ro" "$image" sh -ec \
  'python -m pip install --quiet --no-cache-dir --target /tmp/test-deps "pytest>=8,<10" && python -m pytest -q -p no:cacheprovider /checks/upstream/test_units.py /checks/upstream/test_almanac.py'
mkdir -p .build/fixtures
model_cache=${PAPERCUT_TEST_MODEL_CACHE:-$PWD/.build/model-cache}
mkdir -p "$model_cache"
curl --fail --location --retry 2 --max-time 180 \
  https://wsp-lab.github.io/papers/lee-sp26.pdf -o .build/fixtures/paper.pdf
if [[ -z ${PAPERCUT_TEST_MODEL_CACHE:-} ]]; then
  if [[ $(id -u) == 0 ]]; then
    chown 99:100 "$model_cache"
  else
    sudo chown 99:100 "$model_cache"
  fi
fi
docker run "${common[@]}" -e PYTHONPATH=/opt/papercut \
  -e HF_HUB_DISABLE_TELEMETRY=1 -e DO_NOT_TRACK=1 \
  -v "$PWD/tests:/checks:ro" -v "$PWD/.build/fixtures:/fixtures:ro" \
  -v "$model_cache:/cache" "$image" python /checks/check_fidelity.py
