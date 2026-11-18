#!/usr/bin/env bash
# Docker acceptance test: the real flow, end to end.
# Runs as its own compose project with its own volume and port, so the real `ngui-data` is never touched.
# Usage: scripts/acceptance.sh [core-repo-url]
set -euo pipefail
cd "$(dirname "$0")/.."

CORE=${1:-https://github.com/ilkermansur/nicegui-core-plugins}
PORT=${ACCEPT_PORT:-18081}
URL="http://127.0.0.1:$PORT"
OVR=$(mktemp)
trap 'rm -f "$OVR"' EXIT
cat > "$OVR" <<EOF
services:
  app:
    environment: {NGUI_CORE_REPO: "$CORE", NGUI_LANG: en, GITHUB_TOKEN: ""}
EOF
export NGUI_HOST_PORT=$PORT
dc() { docker compose -p ngui-accept -f docker-compose.yml -f "$OVR" "$@"; }
ngui() { dc exec -T -e GIT_AUTHOR_NAME=t -e GIT_AUTHOR_EMAIL=t@t -e GIT_COMMITTER_NAME=t -e GIT_COMMITTER_EMAIL=t@t app ngui "$@"; }
pass() { echo "  ok  $1"; }
fail() { echo "  FAIL $1"; dc logs --tail 40 app; exit 1; }

# page <path> <must-contain>: waits for the app (it restarts after every change), then checks the page
page() {
  for _ in $(seq 60); do
    body=$(curl -fsS "$URL$1" 2>/dev/null) && grep -q -- "$2" <<<"$body" && return 0
    sleep 1
  done
  return 1
}

echo "== fresh volume, build and boot"
dc down -v --remove-orphans >/dev/null 2>&1 || true
dc up -d --build >/dev/null 2>&1
page / ngui-topbar && pass "home page served inside the layout" || fail "home page"
list=$(ngui list)
for p in storage-sqlite auth-local theme-default layout-sidebar store; do
  grep -q "^$p	core	✓" <<<"$list" || fail "core plugin $p listed and enabled"
done
[ "$(awk -F'\t' '$6!=""' <<<"$list")" = "" ] && pass "five core plugins from GitHub, no problems" || fail "problems: $list"

echo "== add, disable, enable, remove a plugin"
dc exec -T app sh -c 'rm -rf /tmp/p && mkdir /tmp/p' && ngui new demo --dir /tmp/p >/dev/null
ngui add /tmp/p/nicegui-plugin-demo >/dev/null
page /demo ngui-topbar && pass "added plugin's page is served in the layout" || fail "demo page"
page / '/demo' && pass "added plugin is in the menu" || fail "demo in menu"
ngui disable demo >/dev/null; sleep 3
page / ngui-topbar && ! curl -fsS "$URL/" | grep -q '/demo' && pass "disabled plugin leaves the menu" || fail "disable"
ngui enable demo >/dev/null; sleep 3
page / '/demo' && pass "re-enabled plugin is back" || fail "enable"

echo "== a broken plugin does not take the app down"
ngui new boom --dir /tmp/p >/dev/null
dc exec -T app sh -c 'cd /tmp/p/nicegui-plugin-boom && printf "import sys\nsys.exit(1)\n" > __init__.py &&
  git -c user.name=t -c user.email=t@t commit -qam boom'
ngui add /tmp/p/nicegui-plugin-boom >/dev/null; sleep 3
page /demo ngui-topbar && pass "app and other plugins still up with a plugin that calls sys.exit" || fail "broken plugin"
ngui remove boom >/dev/null; sleep 3

echo "== core update and refusals"
ngui update core >/dev/null && pass "ngui update core" || fail "update core"
! ngui remove core-plugins >/dev/null 2>&1 && dc exec -T app test -d /data/repos/core-plugins/store \
  && pass "core-plugins cannot be removed" || fail "core-plugins guard"

echo "== state survives restart and rebuild"
dc down >/dev/null 2>&1; dc up -d >/dev/null 2>&1
page / '/demo' && pass "after down/up: demo still installed and enabled" || fail "down/up"
dc up -d --build --force-recreate >/dev/null 2>&1
page / '/demo' && pass "after rebuild: state kept in the volume" || fail "rebuild"
ngui remove demo >/dev/null; sleep 3
page / ngui-topbar && ! curl -fsS "$URL/" | grep -q '/demo' && pass "removed plugin is gone" || fail "remove"

dc down -v >/dev/null 2>&1
echo "ALL PASSED"
