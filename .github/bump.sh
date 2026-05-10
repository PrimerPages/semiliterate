#!/bin/bash
set -euo pipefail

DRY_RUN=false
VERSION="${VERSION:-}"
PYPROJECT_FILE="pyproject.toml"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --version"
        exit 1
      fi
      VERSION="$2"
      shift 2
      ;;
    --file|--pyproject|--pyproject-file)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for $1"
        exit 1
      fi
      PYPROJECT_FILE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -*)
      echo "Unknown flag: $1"
      exit 1
      ;;
    *)
      if [[ -z "$VERSION" ]]; then
        VERSION="$1"
        shift
      else
        echo "Unexpected argument: $1"
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "Usage: $0 [--version VERSION] [--pyproject-file FILE] [--dry-run]"
  exit 1
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Invalid version format: $VERSION"
  echo "Expected format: x.y.z (for example, 1.2.3)"
  exit 1
fi

if [[ ! -f "$PYPROJECT_FILE" ]]; then
  echo "Pyproject file not found: $PYPROJECT_FILE"
  exit 1
fi

echo "Bumping version to $VERSION in $PYPROJECT_FILE"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "[DRY RUN] Would update version to $VERSION in $PYPROJECT_FILE"
  exit 0
fi

sed -i.bak -E 's/^version = "[^"]+"$/version = "'"$VERSION"'"/' "$PYPROJECT_FILE"
rm -f "$PYPROJECT_FILE.bak"

echo "Updated to version $VERSION"
