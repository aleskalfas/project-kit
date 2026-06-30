#!/usr/bin/env bash
# Thin wrapper: record the greenfield-setup demo with this bundle's config.
exec pkit demo-recording record greenfield-setup \
  --config "$(dirname "$0")/record.yaml" "$@"
