#!/usr/bin/env bash
#
# Fetch the Android prebuilt clang that built this kernel's vendor image.
#
# Why this is a script and not an inline CI step: the download is the one part
# of the pipeline that depends on a third party, so it has to be exercised
# locally (see docs/TOOLCHAIN.md) instead of only discovered broken in CI.
#
# Exit codes, so the caller can tell the two failures apart:
#   0   toolchain present and verified
#   65  wrong or corrupt content arrived (do NOT retry, do not fall back silently)
#   75  network exhausted (caller decides whether to fall back)
#
set -euo pipefail

: "${DEST:?DEST must point at the toolchain directory}"
: "${CLANG_PREBUILT_DIR:=clang-r596125}"
: "${CLANG_PREBUILT_SHA:=29182889399818f97baa65ea238c80e8117981eb}"
: "${ATTEMPTS:=3}"
: "${EXPECT_ANDROID_VERSION:=22.0.2}"
: "${EXPECT_BUILD:=15071444}"

ARCHIVE_URL="${TOOLCHAIN_ARCHIVE_URL:-https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+archive/${CLANG_PREBUILT_SHA}/${CLANG_PREBUILT_DIR}.tar.gz}"

log() { printf '%s\n' "$*" >&2; }

if [ -x "$DEST/bin/clang" ]; then
  log "toolchain already present at $DEST"
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

check_content() {
  # $1 = archive. Returns 0 when it is the prebuilt we asked for.
  local archive="$1" top
  # A repository archive (the mistake gitiles makes when ?path= is used) starts
  # at .gitignore; the directory archive starts at AndroidVersion.txt. Reading
  # only the first member keeps this cheap.
  top="$(tar -tzf "$archive" 2>/dev/null | head -1 || true)"
  if [ "$top" != 'AndroidVersion.txt' ]; then
    log "archive starts at '${top:-<unreadable>}', expected AndroidVersion.txt"
    return 1
  fi
  # gzip -t catches truncation, which a short read produces without any error.
  gzip -t "$archive" || { log 'archive fails gzip integrity check (truncated?)'; return 1; }
  return 0
}

attempt=1
while [ "$attempt" -le "$ATTEMPTS" ]; do
  part="$TMP/clang.tar.gz"
  rm -f "$part"
  log "attempt $attempt/$ATTEMPTS: $ARCHIVE_URL"

  # gitiles builds this archive on demand and ignores Range: asking for bytes
  # 100-200 of an interrupted download answers 200 with the whole stream from
  # byte 0. So --continue-at cannot work here (curl exits 33 "does not seem to
  # support byte ranges"), and appending would corrupt the archive. Every
  # attempt is a complete download to a private temporary file instead, which
  # makes a partial transfer harmless.
  rc=0
  # -sS: a progress meter is unreadable in a CI log, but the error message on
  # failure still matters.
  curl -fsSL --retry 3 --retry-delay 5 --retry-all-errors \
       --connect-timeout 30 --max-time 3600 \
       --speed-limit 1024 --speed-time 300 \
       -o "$part" "$ARCHIVE_URL" || rc=$?

  bytes="$(stat -c%s "$part" 2>/dev/null || echo 0)"

  if [ "$rc" -eq 0 ] && check_content "$part"; then
    log "downloaded $bytes bytes; extracting"
    rm -rf "$DEST.tmp"
    mkdir -p "$DEST.tmp"
    if ! tar -xzf "$part" -C "$DEST.tmp"; then
      # Extraction failures are content/environment problems, not network ones:
      # retrying the download would just fail the same way. Report and stop.
      log 'extraction failed; the archive downloaded fully but could not be unpacked'
      rm -rf "$DEST.tmp"
      exit 65
    fi
    # AndroidVersion.txt is the prebuilt's own statement of what it is, and
    # manifest_<build>.xml ties it to the vendor's build number.
    if ! grep -qx "$EXPECT_ANDROID_VERSION" "$DEST.tmp/AndroidVersion.txt" 2>/dev/null; then
      log "unexpected AndroidVersion.txt: $(tr '\n' ' ' < "$DEST.tmp/AndroidVersion.txt" 2>/dev/null)"
      rm -rf "$DEST.tmp"
      exit 65
    fi
    if [ ! -f "$DEST.tmp/manifest_${EXPECT_BUILD}.xml" ]; then
      log "expected manifest_${EXPECT_BUILD}.xml; got: $(ls "$DEST.tmp"/manifest_*.xml 2>/dev/null | xargs -n1 basename 2>/dev/null | tr '\n' ' ')"
      rm -rf "$DEST.tmp"
      exit 65
    fi
    # Rename only once everything above passed, so DEST is never half-written.
    rm -rf "$DEST"
    mv "$DEST.tmp" "$DEST"
    log "toolchain ready: $("$DEST/bin/clang" --version | head -1)"
    exit 0
  fi

  if [ "$rc" -eq 0 ]; then
    # Transfer "succeeded" but the bytes are wrong/truncated. Worth one more
    # whole attempt, since a dropped chunked stream can look complete.
    log "attempt $attempt produced unusable content (${bytes} bytes)"
    backoff=$((attempt * 20))
  else
    log "attempt $attempt failed (curl exit $rc) after ${bytes} bytes"
    backoff=$((attempt * 30))
  fi
  if [ "$attempt" -lt "$ATTEMPTS" ]; then
    log "retrying in ${backoff}s"
    sleep "$backoff"
  fi
  attempt=$((attempt + 1))
done

log "could not fetch $ARCHIVE_URL after $ATTEMPTS attempts"
exit 75
