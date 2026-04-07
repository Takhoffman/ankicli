#!/bin/sh

set -eu

REPO="${ANKICLI_REPO:-Takhoffman/ankicli}"
RAW_BASE="${ANKICLI_RAW_BASE:-https://raw.githubusercontent.com/$REPO/main}"
RELEASES_BASE="${ANKICLI_RELEASES_BASE:-https://github.com/$REPO/releases}"
VERSION="${VERSION:-${ANKICLI_INSTALL_VERSION:-latest}}"
BIN_DIR="${ANKICLI_INSTALL_BIN_DIR:-$HOME/.local/bin}"
INSTALL_ROOT="${ANKICLI_INSTALL_ROOT:-$HOME/.local/share/ankicli}"
TMP_DIR="${TMPDIR:-/tmp}"
VERIFY="${ANKICLI_SKIP_VERIFY:-0}"

log() {
  printf '%s\n' "$*"
}

fail() {
  printf 'ankicli install error: %s\n' "$*" >&2
  exit 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

detect_target() {
  if [ -n "${ANKICLI_TARGET:-}" ]; then
    printf '%s' "$ANKICLI_TARGET"
    return
  fi

  os="$(uname -s)"
  arch="$(uname -m)"
  case "$os" in
    Darwin) os_slug="darwin" ;;
    Linux) os_slug="linux" ;;
    *) fail "unsupported operating system: $os" ;;
  esac

  case "$arch" in
    x86_64|amd64) arch_slug="x64" ;;
    arm64|aarch64)
      if [ "$os_slug" = "linux" ]; then
        fail "unsupported architecture for Linux installer: $arch"
      fi
      arch_slug="arm64"
      ;;
    *) fail "unsupported architecture: $arch" ;;
  esac

  printf '%s-%s' "$os_slug" "$arch_slug"
}

resolve_version() {
  if [ "$VERSION" != "latest" ]; then
    printf '%s' "$VERSION"
    return
  fi

  if [ -n "${ANKICLI_LATEST_VERSION:-}" ]; then
    printf '%s' "$ANKICLI_LATEST_VERSION"
    return
  fi

  need curl
  release_json="$(curl -fsSL "${ANKICLI_RELEASE_API:-https://api.github.com/repos/$REPO/releases/latest}")" ||
    fail "could not resolve latest release"
  version="$(printf '%s' "$release_json" | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"v\{0,1\}\([^"]*\)".*/\1/p' | head -n 1)"
  [ -n "$version" ] || fail "latest release response did not include a tag_name"
  printf '%s' "$version"
}

download() {
  url="$1"
  output="$2"
  need curl
  curl -fsSL "$url" -o "$output" || fail "failed to download $url"
}

verify_checksum() {
  archive_path="$1"
  checksums_path="$2"
  expected="$(awk -v name="$(basename "$archive_path")" '$2 == name { print $1 }' "$checksums_path")"
  [ -n "$expected" ] || fail "missing checksum for $(basename "$archive_path")"
  if command -v shasum >/dev/null 2>&1; then
    actual="$(shasum -a 256 "$archive_path" | awk '{print $1}')"
  elif command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "$archive_path" | awk '{print $1}')"
  else
    fail "missing required checksum command: shasum or sha256sum"
  fi
  [ "$expected" = "$actual" ] || fail "checksum mismatch for $(basename "$archive_path")"
}

extract_archive() {
  archive_path="$1"
  destination="$2"
  mkdir -p "$destination"
  tar -xzf "$archive_path" -C "$destination" || fail "failed to extract archive"
}

main() {
  need tar
  need curl

  target="$(detect_target)"
  version="$(resolve_version)"
  archive_name="ankicli-$version-$target.tar.gz"
  checksums_name="ankicli-$version-checksums.txt"
  release_tag="v$version"

  workdir="$(mktemp -d "$TMP_DIR/ankicli-install.XXXXXX")"
  archive_path="$workdir/$archive_name"
  checksums_path="$workdir/$checksums_name"
  extract_dir="$workdir/extract"

  download "$RELEASES_BASE/download/$release_tag/$archive_name" "$archive_path"
  download "$RELEASES_BASE/download/$release_tag/$checksums_name" "$checksums_path"

  verify_checksum "$archive_path" "$checksums_path"
  extract_archive "$archive_path" "$extract_dir"

  payload_dir="$(find "$extract_dir" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  [ -n "$payload_dir" ] || fail "release archive did not contain a payload directory"
  executable_path="$payload_dir/ankicli"
  [ -x "$executable_path" ] || fail "release archive did not contain ankicli"

  mkdir -p "$INSTALL_ROOT"
  mkdir -p "$BIN_DIR"
  install_dir="$INSTALL_ROOT/$version"
  rm -rf "$install_dir"
  mkdir -p "$install_dir"
  cp -R "$payload_dir"/. "$install_dir/"
  chmod 755 "$install_dir/ankicli"
  ln -sf "$install_dir/ankicli" "$BIN_DIR/ankicli"

  log "Installed ankicli $version to $BIN_DIR/ankicli"

  case ":$PATH:" in
    *":$BIN_DIR:"*) path_ready="1" ;;
    *) path_ready="0" ;;
  esac

  if [ "$path_ready" != "1" ]; then
    log ""
    log "Add this directory to your PATH if needed:"
    log "  export PATH=\"$BIN_DIR:\$PATH\""
  fi

  if [ "$VERIFY" != "1" ]; then
    "$install_dir/ankicli" --version
    "$install_dir/ankicli" --json doctor backend
  fi
}

main "$@"
