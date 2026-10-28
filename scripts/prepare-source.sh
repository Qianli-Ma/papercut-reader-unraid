#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source_url=https://github.com/OxO-106/Papercut.git
requested_ref=${1:-main}
if [[ ! "$requested_ref" =~ ^[A-Za-z0-9._/-]+$ || "$requested_ref" == -* || "$requested_ref" == *..* ]]; then
  printf '%s\n' 'Invalid upstream ref' >&2
  exit 1
fi
mkdir -p .build
if [[ -e .build/source ]]; then
  printf '%s\n' '.build/source already exists; use a fresh checkout/build directory.' >&2
  exit 1
fi
git init --quiet .build/source
git -C .build/source remote add origin "$source_url"
git -C .build/source fetch --depth=1 origin "$requested_ref"
git -C .build/source checkout --quiet --detach FETCH_HEAD
upstream_sha=$(git -C .build/source rev-parse HEAD)
git -C .build/source apply --check "$PWD/patches/reader-only.patch"
git -C .build/source apply "$PWD/patches/reader-only.patch"
git -C .build/source diff --check
mkdir -p .build/deployment
cp deployment/Dockerfile deployment/requirements.lock .build/deployment/
printf '%s\n' "$upstream_sha" > .build/upstream-commit
cat > .build/.dockerignore <<'IGNORE'
**
!deployment/
!deployment/Dockerfile
!deployment/requirements.lock
!source/
!source/app/
!source/app/**
!source/web/
!source/web/**
!source/LICENSE
IGNORE
printf 'Prepared upstream commit %s with reader-only/visual-fidelity patch.\n' "$upstream_sha"
