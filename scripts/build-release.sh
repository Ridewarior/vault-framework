#!/bin/sh
set -eu
out=${1:?Supply an output directory}
mkdir -p "$out"
for platform in linux darwin windows; do
  for arch in amd64 arm64; do
    name="vault-$platform-$arch"
    if [ "$platform" = windows ]; then name="$name.exe"; fi
    CGO_ENABLED=0 GOOS="$platform" GOARCH="$arch" go build -trimpath -o "$out/$name" .
  done
done
cp scripts/launch-vault.sh "$out/"
(cd "$out" && sha256sum vault-* launch-vault.sh > SHA256SUMS)
