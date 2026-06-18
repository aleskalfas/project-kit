#!/usr/bin/env bash
# ffmpeg_post.sh — optional post-processing of a screencapture-produced
# .mov.  Two jobs in one pass:
#
#   1. Container-swap to .mp4 (better player support, +faststart for
#      streaming-friendly playback).
#   2. Re-encode the H.264 stream with proper quality + colour metadata
#      so:
#        - colours match the source (Display P3 tag set);
#        - file is dramatically smaller — screencapture's realtime
#          encoder produces ~5× larger files than a CRF-23 offline pass
#          for typical terminal content.
#
# Three paths, tried in order:
#   C) Re-encode at H.264 CRF (env DCR_CRF, default 23) with P3 colour
#      tags baked in.  Default behaviour.  Wall-clock ~5-10s per
#      90-second take on Apple silicon.  Yields ~85% smaller .mp4 for
#      terminal-text content.
#   B) -c copy + h264_metadata bsf — retag colour metadata only, no
#      re-encode.  Same size as source.  Used when DCR_NO_REENCODE=1
#      or when libx264 isn't available.
#   A) -c copy — plain container swap.  No quality, no colour fix.
#      Final fallback.
#
# After a successful conversion the source .mov is DELETED by default
# (the .mp4 is the keep-worthy artefact and the .mov is just an
# intermediate).  Set DCR_KEEP_MOV=1 to keep both.  If the conversion
# fails, the .mov is always preserved as the fallback artefact.
#
# Skips silently if ffmpeg isn't installed (the .mov stays put).
# Env vars:
#   DCR_NO_POSTPROCESS=1   — skip entirely
#   DCR_NO_REENCODE=1      — use path B (no re-encode) instead of C
#   DCR_KEEP_MOV=1         — keep the source .mov after successful
#                            conversion (default: delete)
#   DCR_CRF=<n>            — H.264 quality (default 23; lower=larger+nicer,
#                            higher=smaller+lossier; 28 is still fine for
#                            terminal text)

set -uo pipefail

INPUT="${1:-}"
if [[ -z "$INPUT" || ! -f "$INPUT" ]]; then
    echo "ffmpeg_post.sh: no input file: ${INPUT:-<unset>}" >&2
    exit 1
fi

if [[ "${DCR_NO_POSTPROCESS:-0}" == "1" ]]; then
    echo "(post-process skipped — DCR_NO_POSTPROCESS=1)"
    exit 0
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "(post-process skipped — ffmpeg not on PATH; install via 'brew install ffmpeg' to get smaller .mp4 + colour fix)"
    exit 0
fi

OUTPUT="${INPUT%.mov}.mp4"
CRF="${DCR_CRF:-23}"

# Helper: called from every success exit path.  If DCR_KEEP_MOV is
# not set to 1, deletes the source .mov.  Always succeeds.
_drop_mov_unless_kept() {
    if [[ "${DCR_KEEP_MOV:-0}" == "1" ]]; then
        echo "  (kept .mov: $INPUT — DCR_KEEP_MOV=1)"
    else
        rm -f -- "$INPUT" && echo "  (removed .mov source: $INPUT)"
    fi
}

# Display P3 colour tag set — applies to both path B (bitstream metadata)
# and path C (encoder flags).
#   primaries: smpte432    (Display P3, ISO numeric 12)
#   transfer:  iec61966-2-1 (sRGB,        ISO numeric 13)
#   matrix:    bt709        (Y'CbCr→RGB,   ISO numeric 1)
P3_PRIMARIES="smpte432"
P3_TRANSFER="iec61966-2-1"
P3_MATRIX="bt709"

src_bytes=$(stat -f%z "$INPUT" 2>/dev/null || stat -c%s "$INPUT" 2>/dev/null || echo 0)

# --- Path C: re-encode H.264 CRF (default) -----------------------------------
if [[ "${DCR_NO_REENCODE:-0}" != "1" ]]; then
    if ffmpeg -y -i "$INPUT" \
        -c:v libx264 -crf "$CRF" -preset medium -pix_fmt yuv420p \
        -color_primaries "$P3_PRIMARIES" -color_trc "$P3_TRANSFER" -colorspace "$P3_MATRIX" \
        -movflags +faststart \
        -an \
        -loglevel error \
        "$OUTPUT" </dev/null 2>&1; then
        dst_bytes=$(stat -f%z "$OUTPUT" 2>/dev/null || stat -c%s "$OUTPUT" 2>/dev/null || echo 0)
        if (( src_bytes > 0 )); then
            pct=$(( 100 - (dst_bytes * 100 / src_bytes) ))
            echo "Post-process [C: H.264 CRF $CRF + P3] → $OUTPUT ($(numfmt --to=iec "$src_bytes" 2>/dev/null || echo "$src_bytes") → $(numfmt --to=iec "$dst_bytes" 2>/dev/null || echo "$dst_bytes"), -${pct}%)"
        else
            echo "Post-process [C: H.264 CRF $CRF + P3] → $OUTPUT"
        fi
        _drop_mov_unless_kept
        exit 0
    fi
    echo "(re-encode failed; falling back to no-encode retag)"
fi

# --- Path B: -c copy + h264_metadata bitstream filter ------------------------
# colour_primaries=12, transfer_characteristics=13, matrix_coefficients=1 are
# the numeric IDs for the named constants above (ffmpeg bsf needs numbers).
B_FILTER="h264_metadata=colour_primaries=12:transfer_characteristics=13:matrix_coefficients=1"
if ffmpeg -y -i "$INPUT" -c copy -bsf:v "$B_FILTER" -loglevel error "$OUTPUT" </dev/null 2>&1; then
    echo "Post-process [B: re-tag P3 + .mp4, no re-encode] → $OUTPUT"
    _drop_mov_unless_kept
    exit 0
fi

# --- Path A: plain container swap --------------------------------------------
echo "(re-tag bitstream filter failed; falling back to container swap)"
if ffmpeg -y -i "$INPUT" -c copy -loglevel error "$OUTPUT" </dev/null 2>&1; then
    echo "Post-process [A: .mp4 only, colours unchanged] → $OUTPUT"
    _drop_mov_unless_kept
    exit 0
fi

echo "(post-process failed; .mov preserved at $INPUT)" >&2
exit 1
