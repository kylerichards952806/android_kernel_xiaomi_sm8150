#!/usr/bin/env bash
#
# Compare a clang toolchain found inside a ROM dump against the one this kernel
# is actually built with. Answers one question: is the compiler in the ROM
# byte-for-byte the one CI downloads, or only something that reports the same
# version string?
#
# The reference can be either a directory (when you have the prebuilt locally)
# or the toolchain-manifest.txt that ships with the kernel artifacts, which is
# what you normally have — it is a few hundred KB instead of 2.4 GB.
#
#   ./scripts/compare-toolchain.sh /path/to/rom/prebuilts/clang/host/linux-x86/clang-r596125
#   ./scripts/compare-toolchain.sh /path/to/rom-dump            # searches for it
#   ./scripts/compare-toolchain.sh <rom-path> <manifest-or-dir>
#
set -uo pipefail

ROM_PATH="${1:-}"
REF_PATH="${2:-${REF_TOOLCHAIN:-}}"

log() { printf '%s\n' "$*"; }
hr()  { printf '%s\n' '------------------------------------------------------------'; }

if [ -z "$ROM_PATH" ]; then
  echo "usage: $0 <rom-toolchain-dir|rom-root> [manifest.txt|reference-toolchain-dir]" >&2
  exit 2
fi
[ -e "$ROM_PATH" ] || { echo "no such path: $ROM_PATH" >&2; exit 2; }

REF_MANIFEST=0
if [ -n "$REF_PATH" ] && [ -f "$REF_PATH" ]; then
  REF_MANIFEST=1
fi

# Find the toolchain directory if the caller pointed at a ROM root.
if [ ! -f "$ROM_PATH/AndroidVersion.txt" ]; then
  found="$(find "$ROM_PATH" -maxdepth 7 -type f -name AndroidVersion.txt 2>/dev/null \
            | while read -r f; do
                grep -qi 'clang\|^2[0-9]\.' "$f" 2>/dev/null && dirname "$f"
              done | head -3)"
  if [ -z "$found" ]; then
    echo "could not find a clang toolchain (AndroidVersion.txt) under $ROM_PATH" >&2
    exit 2
  fi
  if [ "$(printf '%s\n' "$found" | wc -l)" -gt 1 ]; then
    log "several toolchains found; comparing the first:"
    printf '  %s\n' $found
  fi
  ROM_PATH="$(printf '%s\n' "$found" | head -1)"
fi

log "ROM toolchain:       $ROM_PATH"
log "AndroidVersion.txt:  $(tr '\n' ' ' < "$ROM_PATH/AndroidVersion.txt" 2>/dev/null)"
[ "$REF_MANIFEST" = 1 ] && log "reference:           manifest $REF_PATH"

# ---------------------------------------------------------------- helpers ---
version_of_dir() {
  local dir="$1"
  if [ ! -x "$dir/bin/clang" ]; then
    printf 'absent (%s/bin/clang not executable)\n' "$dir"
    return
  fi
  if ! out="$("$dir/bin/clang" --version 2>&1 | head -1)"; then
    printf 'failed to run: %s\n' "$out"
    return
  fi
  printf '%s\n' "$out"
}

manifest_field() { sed -n "s/^# $1: //p" "$REF_PATH" | head -1; }

manifest_of_dir() { ls "$1"/manifest_*.xml 2>/dev/null | head -1 | xargs -r basename; }

inventory() {
  # $1 = dir. "sha256  relative/path" for every regular file, sorted.
  ( cd "$1" && find . -type f -printf '%P\n' 2>/dev/null | LC_ALL=C sort | while IFS= read -r f; do
      printf '%s  %s\n' "$(sha256sum "$f" 2>/dev/null | cut -d' ' -f1)" "$f"
    done )
}

manifest_inventory() { grep -v '^#' "$REF_PATH" | sed 's|  \./|  |' ; }

# ------------------------------------------------------------------ compare --
hr
log "version strings"
ROM_VER="$(version_of_dir "$ROM_PATH")"
log "  ROM: $ROM_VER"
if [ -n "$REF_PATH" ]; then
  if [ "$REF_MANIFEST" = 1 ]; then
    REF_VER="$(manifest_field clang)"
  else
    REF_VER="$(version_of_dir "$REF_PATH")"
  fi
  log "  REF: $REF_VER"
  [ "$ROM_VER" = "$REF_VER" ] && log "  => version strings MATCH" || log "  => version strings DIFFER"
fi

hr
log "build id (manifest_<build>.xml)"
ROM_MAN="$(manifest_of_dir "$ROM_PATH")"
log "  ROM: ${ROM_MAN:-<none>}"
if [ -n "$REF_PATH" ]; then
  if [ "$REF_MANIFEST" = 1 ]; then
    REF_MAN="$(manifest_field build-manifest)"
  else
    REF_MAN="$(manifest_of_dir "$REF_PATH")"
  fi
  log "  REF: ${REF_MAN:-<none>}"
  [ "$ROM_MAN" = "$REF_MAN" ] && log "  => build ids MATCH" || log "  => build ids DIFFER"
fi

hr
log "key binaries"
if [ "$REF_MANIFEST" = 1 ]; then manifest_inventory > "${TMPDIR:-/tmp}/ref-inv.$$" 2>/dev/null || true; fi
for f in bin/clang bin/ld.lld bin/llvm-objcopy; do
  r="$(sha256sum "$ROM_PATH/$f" 2>/dev/null | cut -d' ' -f1)"
  printf '  %-18s ROM %s\n' "$f" "${r:-<missing>}"
  if [ -n "$REF_PATH" ]; then
    if [ "$REF_MANIFEST" = 1 ]; then
      s="$(grep -E "  ${f//\//\\/}$" "$REF_PATH" | cut -d' ' -f1 | head -1)"
    else
      s="$(sha256sum "$REF_PATH/$f" 2>/dev/null | cut -d' ' -f1)"
    fi
    printf '  %-18s REF %s  %s\n' "" "${s:-<missing>}" \
      "$([ -n "$r" ] && [ "$r" = "$s" ] && echo MATCH || echo DIFFER)"
  fi
done

if [ -z "$REF_PATH" ]; then
  hr
  log "No reference given (pass a manifest or a directory, or set REF_TOOLCHAIN)."
  log "Skipping the inventory diff."
  exit 0
fi

hr
log "full inventory diff (sha256 of every file)"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
inventory "$ROM_PATH" | LC_ALL=C sort > "$TMPD/rom.txt"
if [ "$REF_MANIFEST" = 1 ]; then
  manifest_inventory | LC_ALL=C sort > "$TMPD/ref.txt"
else
  inventory "$REF_PATH" | LC_ALL=C sort > "$TMPD/ref.txt"
fi
rom_n=$(wc -l < "$TMPD/rom.txt"); ref_n=$(wc -l < "$TMPD/ref.txt")
log "  files: ROM $rom_n, REF $ref_n"
same=$(comm -12 "$TMPD/rom.txt" "$TMPD/ref.txt" | wc -l)
log "  identical (path+hash): $same"
missing="$(comm -23 <(cut -d'  ' -f2- "$TMPD/rom.txt" | sort) <(cut -d'  ' -f2- "$TMPD/ref.txt" | sort) | wc -l)"
extra="$(comm -13 <(cut -d'  ' -f2- "$TMPD/rom.txt" | sort) <(cut -d'  ' -f2- "$TMPD/ref.txt" | sort) | wc -l)"
log "  paths only in ROM: $missing, paths only in REF: $extra"
if cmp -s "$TMPD/rom.txt" "$TMPD/ref.txt"; then
  log "  => the two trees are byte-for-byte identical"
else
  log "  differing entries (path, then hashes):"
  diff "$TMPD/rom.txt" "$TMPD/ref.txt" | grep -E '^[<>]' | head -40
  log "  (up to 40 shown)"
fi
