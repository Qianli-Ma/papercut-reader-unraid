# Papercut reader images for Unraid

A CPU-only Linux amd64 image publisher for
[OxO-106/Papercut](https://github.com/OxO-106/Papercut), with a small reader-only
and PDF-fidelity patch. Papercut remains under its upstream MIT license.

The intended image is `ghcr.io/qianli-ma/papercut-reader-unraid:stable`.
A normal Unraid Docker template can pull that tag, compare its registry digest,
and install published updates using Check for Updates / Update.

## Publication gates

The workflow runs on publisher commits, manual dispatch, and a daily upstream
check. Each build records an exact upstream commit, checks that the isolated patch
applies cleanly, and uses a pinned Python base plus hash-locked CPU dependencies.
It publishes only after these checks pass:

1. Installed dependencies satisfy the new upstream requirements.
2. Reader-only mode keeps parsing active and prevents Ollama requests.
3. Upstream pure-logic tests pass.
4. The public acceptance paper parses in an isolated test library. All 15 verified
   original-PDF image crops must match their reviewed SHA-256 hashes, dimensions
   and pages; all 73 bibliography entries and reading-order checkpoints remain.

If upstream breaks the patch, needs newer dependencies, or changes a verified
crop, publication fails and the last working stable tag stays available. It needs
review before an incompatible upstream update can be published. This workflow
does not deploy to any NAS. The user chooses when to apply updates in Unraid.

## Data boundaries

This repository and image contain open-source application code, the deployment
patch, locked dependencies and test scripts. They contain no NAS addresses,
credentials, mounted library, model cache, private PDFs, reading history or Unraid
configuration. The acceptance PDF is downloaded from its public author URL during
testing; it is not committed or included in the image. Downloaded model caches and
test output stay in the ephemeral workflow workspace.

The workflow token has contents-read and packages-write permissions for this
repository. It is not passed into application/test containers, and those containers
have no Docker socket, privileges or NAS access. Official GitHub/Docker actions
are pinned to reviewed release commits. Credentials are not required for users
to pull a public GHCR image.

## Build locally

```sh
bash scripts/prepare-source.sh c2859b23c9214e182c24d211714ae727e998be56
set -a
. deployment/python-base.env
set +a
docker build --platform linux/amd64 \
  --build-arg PYTHON_BASE="$PYTHON_BASE" \
  --build-arg UPSTREAM_COMMIT="$(cat .build/upstream-commit)" \
  -f .build/deployment/Dockerfile -t papercut-reader:candidate .build
bash scripts/test-image.sh papercut-reader:candidate
```

Use a clean `.build/source` directory for each source preparation; the script
refuses to overwrite one. Tests need Docker, Bash, Git, curl and permission to
assign UID 99/GID 100 ownership to their isolated model-cache directory.

## First publication and Unraid setup

1. Create the intended GitHub repository and push these files to its `main` branch.
2. Wait for the first tested workflow build to publish the package.
3. Make the GHCR package public in its Package Settings so Unraid can pull it
   anonymously. GitHub packages default to private, even for a public source repo.
4. Verify anonymous manifest access and native Unraid digest detection before
   changing the running container's Repository to the stable tag.
5. Run the native Unraid Update path, then verify health, original PDFs, crops,
   metadata and reading progress. Retain the previous immutable image for rollback.

Future compatible upstream commits become tested registry images automatically;
Unraid's dashboard handles installing them. The pinned dependency lock changes
only through reviewed publisher commits. A daily job skips rebuilding when both
upstream and publisher revisions match the current stable image.

References: [GitHub's image publishing workflow](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images),
[GHCR visibility and authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
