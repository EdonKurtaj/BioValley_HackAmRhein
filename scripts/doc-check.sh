#!/usr/bin/env bash
# doc-check: finds documentation drift. Lists file paths mentioned in the team docs
# that don't exist in the repo. Warning by default, --strict fails (used before shipping).
#
#   bash scripts/doc-check.sh           warn only (pre-commit hook)
#   bash scripts/doc-check.sh --strict  exit 1 on any finding ($hack-ship, $hack-review)
#
# Checked: README.md, docs/*.md (except plan.md and decisions.md, which may name future
# or historical files), and handoff/*.md files whose status is not "done".
# A token counts as a path if it has a file extension or ends with "/".
# Placeholders with < > or * and local-only paths (.env, .hack/) are ignored.

set -u
STRICT=0; [ "${1:-}" = "--strict" ] && STRICT=1
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 1

FILES="README.md HACKAMRHEIN.md TEAMWORK.md"
for f in docs/*.md; do
  case "$f" in docs/plan.md|docs/decisions.md) continue ;; esac
  [ -f "$f" ] && FILES="$FILES $f"
done
for f in handoff/*.md; do
  [ -f "$f" ] || continue
  [ "$f" = "handoff/README.md" ] && continue
  grep -Eiq '^Status:[[:space:]]*done' "$f" && continue
  FILES="$FILES $f"
done

EXT='py|js|ts|jsx|tsx|mjs|md|csv|tsv|json|ya?ml|toml|txt|html|css|sh|ps1|ipynb|sql|xlsx|parquet|r|R|png|jpg|svg'
FOUND=0
for f in $FILES; do
  [ -f "$f" ] || continue
  # inline code spans plus every word inside fenced code blocks
  awk '
    /^```/ { fence = !fence; next }
    fence  { n = split($0, w, /[[:space:]]+/); for (i=1;i<=n;i++) print w[i]; next }
    { line=$0; while (match(line, /`[^`]+`/)) { print substr(line, RSTART+1, RLENGTH-2); line = substr(line, RSTART+RLENGTH) } }
  ' "$f" | while IFS= read -r tok; do
    tok="${tok%%#*}"; tok="${tok%:}"; tok="${tok%,}"; tok="${tok%)}"; tok="${tok#(}"; tok="${tok#./}"
    tok="$(echo "$tok" | sed -E 's/:[0-9]+$//')"
    [ -z "$tok" ] && continue
    case "$tok" in *.*) ;; feat/*|fix/*|data/*|chore/*|iface/*) continue ;; esac   # branch names (no extension), not paths
    case "$tok" in *" "*|*"<"*|*">"*|*"*"*|http*|/*|"~"*|'$'*|@*|-*|.env*|.hack/*|*"{"*|*"="*) continue ;; esac
    if echo "$tok" | grep -Eq "\.(${EXT})$" || echo "$tok" | grep -Eq '^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)*/$'; then
      [ -e "$tok" ] && continue
      # a bare file name (no folder) is fine if it exists anywhere in the repo
      case "$tok" in */*) ;; *) [ -n "$(find . -path ./.git -prune -o -name "$tok" -print 2>/dev/null | head -1)" ] && continue ;; esac
      echo "  $f mentions '$tok', which doesn't exist"
    fi
  done
done > "${TMPDIR:-/tmp}/doc-check.$$"

if [ -s "${TMPDIR:-/tmp}/doc-check.$$" ]; then
  FOUND=1
  echo
  echo "doc-check: the docs mention files that don't exist (documentation drift):"
  sort -u "${TMPDIR:-/tmp}/doc-check.$$"
  echo "Fix the doc in the same commit as the code, or ask your assistant: \$hack-review."
fi
rm -f "${TMPDIR:-/tmp}/doc-check.$$"

if [ "$FOUND" -eq 1 ] && [ "$STRICT" -eq 1 ]; then exit 1; fi
[ "$FOUND" -eq 0 ] && echo "doc-check: ok"
exit 0
