#!/bin/bash
set -eu
install_root="$HOME/Applications/MarketingCourt"
if [ ! -f "$install_root/Start-Mac.command" ]; then
  printf '正在下载 Marketing Court……\n'
  download_root="$(mktemp -d "${TMPDIR:-/tmp}/marketing-court.XXXXXX")"
  curl --fail --location --retry 3 'https://github.com/BDERyanYU/marketing-court/archive/refs/heads/main.zip' --output "$download_root/project.zip"
  ditto -x -k "$download_root/project.zip" "$download_root"
  mkdir -p "$HOME/Applications"
  ditto "$download_root/marketing-court-main" "$install_root"
  rm "$download_root/project.zip"
fi
chmod +x "$install_root/Start-Mac.command"
mkdir -p "$HOME/Desktop"
ln -sfn "$install_root/Start-Mac.command" "$HOME/Desktop/Marketing Court.command"
printf '以后双击桌面的 Marketing Court 即可打开。\n'
exec /bin/bash "$install_root/scripts/launch-macos.sh"
