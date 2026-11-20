#!/bin/sh
set -eu
case "$(uname -s)" in Linux) platform=linux ;; Darwin) platform=darwin ;; *) echo "Use the Windows download from the release page." >&2; exit 1 ;; esac
case "$(uname -m)" in x86_64|amd64) arch=amd64 ;; arm64|aarch64) arch=arm64 ;; *) echo "Unsupported architecture: $(uname -m)" >&2; exit 1 ;; esac
base=https://github.com/Ridewarior/vault-framework/releases/latest/download
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
curl -fsSL "$base/vault-$platform-$arch" -o "$tmp/vault"
chmod +x "$tmp/vault"
"$tmp/vault" "$@"
