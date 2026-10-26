#!/usr/bin/env bash
# Render every spec with vl2svg. A browser renders nothing and says little;
# vl2svg fails loudly. Pass spec basenames to check only those.
# Errors fail the run. Warnings are printed but do not, because a few are
# unavoidable (shared-scale legend merges across concatenated panels).
cd "$(dirname "$0")"
mkdir -p .preview
list=("$@")
if [ ${#list[@]} -eq 0 ]; then
  list=($(ls specs/*.vl.json | xargs -n1 basename | sed 's/\.vl\.json$//'))
fi
fail=0
for f in "${list[@]}"; do
  out=$(npx -y -p vega-cli@6 -p vega-lite@6 vl2svg -b . "specs/$f.vl.json" ".preview/$f.svg" 2>&1)
  warn=$(echo "$out" | grep -ci 'WARN' || true)
  if [ -s ".preview/$f.svg" ] && ! echo "$out" | grep -qiE '^error|Error:'; then
    printf "  ok    %-34s %8s bytes  %s warn
" "$f" "$(wc -c < ".preview/$f.svg")" "$warn"
    echo "$out" | grep -i 'WARN' | sed 's/^/          /' | sort -u
  else
    fail=1
    printf "  FAIL  %-34s
" "$f"
    echo "$out" | head -6 | sed 's/^/          /'
  fi
done
exit $fail
