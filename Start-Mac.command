#!/bin/bash
set -eu
script_path="$0"
while [ -L "$script_path" ]; do
  script_dir="$(cd "$(dirname "$script_path")" && pwd)"
  script_path="$(readlink "$script_path")"
  case "$script_path" in /*) ;; *) script_path="$script_dir/$script_path" ;; esac
done
cd "$(dirname "$script_path")"
if ! /bin/bash scripts/launch-macos.sh; then
  printf '\n启动未完成，请保留上面的提示并联系项目维护者。\n'
  read -r -p '按回车关闭。' answer
  exit 1
fi
