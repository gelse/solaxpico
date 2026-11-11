#!/usr/bin/env bash
# Ensure the dev container user can access USB serial devices such as /dev/ttyACM0.
# Device group GIDs are host-specific (e.g. uucp on Arch), so we adjust access at startup.
set -euo pipefail

target_user="${TARGET_USER:-${SUDO_USER:-${REMOTE_USER:-developer}}}"
if ! id "$target_user" >/dev/null 2>&1; then
  target_user="$(id -un)"
fi

run_as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

can_access_as_target() {
  local dev="$1"
  if [ "$(id -un)" = "$target_user" ]; then
    [ -r "$dev" ] && [ -w "$dev" ]
  else
    run_as_root su -s /bin/bash "$target_user" -c "[ -r \"$dev\" ] && [ -w \"$dev\" ]"
  fi
}

shopt -s nullglob
devices=(/dev/ttyACM* /dev/ttyUSB*)
shopt -u nullglob

if [ ${#devices[@]} -eq 0 ]; then
  exit 0
fi

for dev in "${devices[@]}"; do
  [ -e "$dev" ] || continue
  gid="$(stat -c '%g' "$dev")"

  # Ensure a group exists for the host GID and add the target user to it.
  if ! getent group "$gid" >/dev/null 2>&1; then
    run_as_root groupadd -g "$gid" "hostserial${gid}" || true
  fi
  gname="$(getent group "$gid" | cut -d: -f1 || true)"
  if [ -n "$gname" ]; then
    run_as_root usermod -aG "$gname" "$target_user" || true
  fi

  # Fallback: guarantee access even if group membership is not yet active in this shell/session.
  # /dev is bind-mounted from the host, so this affects the host device node until replug/reboot.
  if ! can_access_as_target "$dev"; then
    run_as_root chmod 666 "$dev" || true
  fi
done

