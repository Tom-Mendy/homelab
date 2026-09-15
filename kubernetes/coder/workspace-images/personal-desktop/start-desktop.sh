#!/usr/bin/env bash
set -eu

export HOME="${HOME:-/opt/data}"
export DISPLAY="${DISPLAY:-:1}"
export VNC_GEOMETRY="${VNC_GEOMETRY:-1920x1080}"
export VNC_DEPTH="${VNC_DEPTH:-24}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-$(id -u)}"

mkdir -p "$HOME/.vnc" "$HOME/.config" "$HOME/.cache" "$XDG_RUNTIME_DIR"
chmod 700 "$HOME/.vnc" "$XDG_RUNTIME_DIR"

cat > "$HOME/.vnc/xstartup" <<'EOF'
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export XDG_CURRENT_DESKTOP=XFCE
export XDG_SESSION_DESKTOP=xfce
exec dbus-run-session -- startxfce4
EOF
chmod 700 "$HOME/.vnc/xstartup"

# Keep a single desktop session across Coder agent restarts.
if ! pgrep -u "$(id -u)" -f 'Xtigervnc.*:1' >/dev/null 2>&1; then
  tigervncserver "$DISPLAY" \
    -localhost yes \
    -SecurityTypes None \
    -geometry "$VNC_GEOMETRY" \
    -depth "$VNC_DEPTH" \
    -xstartup "$HOME/.vnc/xstartup"
fi

if ! pgrep -u "$(id -u)" -f 'websockify.*6080' >/dev/null 2>&1; then
  nohup websockify --web=/opt/novnc/ 127.0.0.1:6080 127.0.0.1:5901 \
    >"$HOME/.vnc/websockify.log" 2>&1 &
fi

for _attempt in 1 2 3 4 5; do
  if curl --silent --fail --max-time 2 http://127.0.0.1:6080/vnc.html >/dev/null; then
    exit 0
  fi
  sleep 1
done

echo 'noVNC did not become ready on localhost:6080' >&2
exit 1
