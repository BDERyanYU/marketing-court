#!/bin/bash
set -eu
project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"
tools_root="$project_root/data/launcher"
mkdir -p "$tools_root/uv"
uv_exe="$tools_root/uv/uv"
if [ ! -x "$uv_exe" ]; then
  printf '正在准备启动工具，首次运行需要联网……\n'
  case "$(uname -m)" in
    arm64) target=aarch64; sha=437a7d498dd6564d5bf986074249ba1fc600e73da55ae04d7bd4c24d5f149b95 ;;
    x86_64) target=x86_64; sha=ff90020b554cf02ef8008535c9aab6ef27bb7be6b075359300dec79c361df897 ;;
    *) printf '暂不支持这台 Mac 的处理器。\n'; exit 1 ;;
  esac
  archive="$tools_root/uv.tar.gz"
  curl --fail --location --retry 3 "https://github.com/astral-sh/uv/releases/download/0.10.11/uv-$target-apple-darwin.tar.gz" --output "$archive"
  actual="$(shasum -a 256 "$archive" | cut -d ' ' -f 1)"
  if [ "$actual" != "$sha" ]; then printf '启动工具校验失败，请重试。\n'; exit 1; fi
  tar -xzf "$archive" --strip-components=1 -C "$tools_root/uv"
  rm "$archive"
fi
export UV_PYTHON_INSTALL_DIR="$tools_root/python"
export UV_CACHE_DIR="$tools_root/uv-cache"
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
exec "$uv_exe" run --python 3.12 --no-project "$project_root/scripts/launch.py" --uv "$uv_exe" "$@"
