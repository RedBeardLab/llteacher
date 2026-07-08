#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REGION="${AWS_REGION:-us-west-2}"
TAG="${1:-$(git -C "$ROOT" rev-parse --short=12 HEAD)}"
REPOSITORY_URL="$(pulumi -C "$ROOT/infra" stack output ecrRepositoryUrl)"
REGISTRY="${REPOSITORY_URL%%/*}"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"
docker buildx build \
  --platform linux/amd64 \
  --file "$ROOT/Dockerfile.aws" \
  --tag "${REPOSITORY_URL}:${TAG}" \
  --push \
  "$ROOT"

pulumi -C "$ROOT/infra" config set imageTag "$TAG"
echo "Pushed ${REPOSITORY_URL}:${TAG} and updated llteacher:imageTag."
echo "Enable the service with: pulumi -C $ROOT/infra config set deployService true"
