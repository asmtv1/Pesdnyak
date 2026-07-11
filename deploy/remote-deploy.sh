#!/bin/sh
set -eu

APP_ROOT="${APP_ROOT:-/opt/pesdnyak}"
PROJECT_NAME="${PROJECT_NAME:-pesdnyak}"
RELEASE_SHA="${RELEASE_SHA:?RELEASE_SHA is required}"
RELEASE_DIR="$APP_ROOT/releases/$RELEASE_SHA"
CURRENT_LINK="$APP_ROOT/current"
DOCKER_CONFIG_DIR="$APP_ROOT/shared/docker-config"

if [ ! -f "$RELEASE_DIR/compose.prod.yaml" ] || [ ! -f "$RELEASE_DIR/deploy.env" ]; then
    echo "Release files are incomplete: $RELEASE_DIR" >&2
    exit 1
fi

available_kb="$(df -Pk "$APP_ROOT" | awk 'NR == 2 {print $4}')"
if [ "$available_kb" -lt 1048576 ]; then
    echo "Less than 1 GiB is available; refusing to pull a new image" >&2
    exit 1
fi

critical_container_ids="$(
    docker ps \
        --filter 'label=com.docker.compose.project=tgbot' \
        --filter 'status=running' \
        --quiet
)"
if [ -z "$critical_container_ids" ]; then
    echo "Critical tgbot project is not running; refusing an unrelated deployment" >&2
    exit 1
fi

compose_at() {
    release_dir="$1"
    shift
    DOCKER_CONFIG="$DOCKER_CONFIG_DIR" docker compose \
        --project-name "$PROJECT_NAME" \
        --env-file "$release_dir/deploy.env" \
        --file "$release_dir/compose.prod.yaml" \
        "$@"
}

previous_release=""
if [ -L "$CURRENT_LINK" ]; then
    previous_release="$(readlink -f "$CURRENT_LINK")"
fi

rollback() {
    if [ -n "$previous_release" ] && [ -d "$previous_release" ]; then
        echo "Deployment failed, restoring $previous_release" >&2
        ln -sfn "$previous_release" "$CURRENT_LINK"
        compose_at "$previous_release" up -d --remove-orphans --wait --wait-timeout 90 || true
    fi
}

compose_at "$RELEASE_DIR" pull
ln -sfn "$RELEASE_DIR" "$CURRENT_LINK"

if ! compose_at "$RELEASE_DIR" up -d --remove-orphans --wait --wait-timeout 90; then
    rollback
    exit 1
fi

container_id="$(compose_at "$RELEASE_DIR" ps -q bot)"
if [ -z "$container_id" ]; then
    rollback
    echo "Bot container was not created" >&2
    exit 1
fi

container_state="$(docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' "$container_id")"
if [ "$container_state" != "running healthy" ]; then
    compose_at "$RELEASE_DIR" logs --no-color --tail 100 bot >&2 || true
    rollback
    echo "Unexpected bot state: $container_state" >&2
    exit 1
fi

for critical_container_id in $critical_container_ids; do
    critical_state="$(docker inspect --format '{{.State.Status}}' "$critical_container_id")"
    if [ "$critical_state" != "running" ]; then
        rollback
        echo "Critical tgbot container stopped during deployment: $critical_container_id" >&2
        exit 1
    fi
done

compose_at "$RELEASE_DIR" ps
