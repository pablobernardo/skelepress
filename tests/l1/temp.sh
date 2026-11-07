#!/bin/bash
# Public temporary-allocation contracts. Sourced by tests/run.sh.

require_test_temp_helpers() {
  if ! declare -F new_test_tmpfile >/dev/null || ! declare -F new_test_tmpdir >/dev/null; then
    fail "temporary allocation helpers must be defined before fixture probes"
    return 1
  fi
}

run_test_temp_explicit_root_test() {
  require_test_temp_helpers || return 0
  local scratch root file1 file2 dir1 dir2 sandbox code helper invalid output
  # Bootstrap independently; honor an optional caller-owned root explicitly.
  if [[ -n "${TMPDIR:-}" ]]; then
    scratch="$(mktemp -d "${TMPDIR%/}/temp-contract.XXXXXXXX")" || {
      fail "explicit-root test fixture allocation failed"
      return 1
    }
  else
    scratch="$(mktemp -d)" || {
      fail "explicit-root test fixture allocation failed"
      return 1
    }
  fi
  root="${scratch}/caller root with spaces"
  mkdir "$root"
  printf 'unchanged\n' >"${scratch}/sentinel"

  for helper in new_test_tmpfile new_test_tmpdir; do
    code=0
    output="$(TMPDIR="$root/" "$helper" 2>"${scratch}/stderr")" || code=$?
    assert_exit_code 0 "$code" "$helper accepts a caller root with spaces and a trailing slash"
    if [[ "$output" == "$root/"* && "${output#"$root/"}" != */* && -e "$output" && ! -s "${scratch}/stderr" ]]; then
      pass "$helper returns one existing direct child with no diagnostics"
    else
      fail "$helper must return one existing direct child with no diagnostics"
      # Never clean up a returned path outside our owned root.
      continue
    fi
    if [[ "$helper" == new_test_tmpfile ]]; then
      file1="$output"
      file2="$(TMPDIR="$root" new_test_tmpfile)" || return
      if [[ -f "$file1" && ! -L "$file1" && ! -s "$file1" && -f "$file2" && "$file1" != "$file2" ]]; then
        pass "file allocations are empty regular files with unique paths"
      else
        fail "file allocations must be empty regular files with unique paths"
      fi
    else
      dir1="$output"
      dir2="$(TMPDIR="$root" new_test_tmpdir)" || return
      if [[ -d "$dir1" && ! -L "$dir1" && -d "$dir2" && "$dir1" != "$dir2" ]]; then
        pass "directory allocations are directories with unique paths"
      else
        fail "directory allocations must be directories with unique paths"
      fi
    fi
  done

  # Inspect only the owned fixture, including hidden entries.
  if "$REAL_PYTHON3" - "$root" "${file1:-}" "${file2:-}" "${dir1:-}" "${dir2:-}" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
expected = {Path(p) for p in sys.argv[2:] if p}
assert len(expected) == 4
assert set(root.iterdir()) == expected
assert all(p.parent == root for p in expected)
assert all(not list(p.iterdir()) for p in expected if p.is_dir())
PY
  then
    pass "allocations create exactly four direct children and no unexpected files"
  else
    fail "allocations must not create unexpected files"
  fi

  code=0
  sandbox="$(TMPDIR="$root" new_contract_sandbox 2>"${scratch}/stderr")" || code=$?
  assert_exit_code 0 "$code" "contract sandbox accepts the caller root"
  if [[ "$sandbox" == "$root/"* && "${sandbox#"$root/"}" != */* && -d "$sandbox" && -f "$sandbox/bin/skelepress" && -f "$sandbox/templates/default.tex" && ! -s "${scratch}/stderr" ]]; then
    pass "contract sandbox material stays under the caller root"
  else
    fail "contract sandbox must return a populated child of the caller root without diagnostics"
  fi

  for invalid in "${scratch}/missing root" "${scratch}/sentinel"; do
    for helper in new_test_tmpfile new_test_tmpdir new_contract_sandbox; do
      # Snapshot the complete owned fixture before each rejected allocation.
      "$REAL_PYTHON3" - "$scratch" >"${scratch}/before" <<'PY'
import hashlib
import sys
from pathlib import Path
root = Path(sys.argv[1])
for p in sorted(root.rglob('*')):
    if p.parent == root and p.name in {'before', 'after', 'stderr'}:
        continue
    print(p.relative_to(root), 'dir' if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest())
PY
      code=0
      output="$(TMPDIR="$invalid" "$helper" 2>"${scratch}/stderr")" || code=$?
      if [[ "$code" -ne 0 && -z "$output" && -s "${scratch}/stderr" ]]; then
        pass "$helper rejects invalid root $(basename "$invalid") with nonzero status, empty stdout and diagnostics"
      else
        fail "$helper must reject invalid roots without fallback (status=$code, stdout=$output)"
      fi
      "$REAL_PYTHON3" - "$scratch" >"${scratch}/after" <<'PY'
import hashlib
import sys
from pathlib import Path
root = Path(sys.argv[1])
for p in sorted(root.rglob('*')):
    if p.parent == root and p.name in {'before', 'after', 'stderr'}:
        continue
    print(p.relative_to(root), 'dir' if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest())
PY
      if cmp -s "${scratch}/before" "${scratch}/after" && [[ ! -e "${scratch}/missing root" && "$(<"${scratch}/sentinel")" == unchanged ]]; then
        pass "$helper leaves directories, fixture material and sentinel unchanged on rejection"
      else
        fail "$helper must leave all owned fixture state unchanged on rejection"
      fi
    done
  done
  # Only this newly allocated fixture is removed; never the caller's TMPDIR.
  rm -rf -- "$scratch"
}

run_test_temp_native_defaults_test() {
  # Native defaults may allocate outside the caller root, by design.
  # Exercise them without a PATH or environment shim.
  require_test_temp_helpers || return 0
  local mode helper output code scratch
  # Use an optional caller-owned root, otherwise preserve native defaults.
  if [[ -n "${TMPDIR:-}" ]]; then
    scratch="$(mktemp -d "${TMPDIR%/}/temp-defaults.XXXXXXXX")" || {
      fail "native-default test fixture allocation failed"
      return 1
    }
  else
    scratch="$(mktemp -d)" || {
      fail "native-default test fixture allocation failed"
      return 1
    }
  fi
  for mode in unset empty; do
    for helper in new_test_tmpfile new_test_tmpdir; do
      code=0
      if [[ "$mode" == unset ]]; then
        output="$(unset TMPDIR; "$helper" 2>"${scratch}/stderr")" || code=$?
      else
        output="$(TMPDIR='' "$helper" 2>"${scratch}/stderr")" || code=$?
      fi
      assert_exit_code 0 "$code" "$helper preserves native allocation with TMPDIR $mode"
      if [[ -n "$output" && "$output" != *$'\n'* && ! -s "${scratch}/stderr" ]] &&
         { [[ "$helper" == new_test_tmpfile && -f "$output" && ! -s "$output" ]] ||
           [[ "$helper" == new_test_tmpdir && -d "$output" ]]; }; then
        pass "$helper returns an existing native allocation without diagnostics with TMPDIR $mode"
        # This path was returned by this successful allocation, not discovered.
        if [[ "$helper" == new_test_tmpdir ]]; then
          rmdir -- "$output"
        else
          rm -f -- "$output"
        fi
      else
        fail "$helper must preserve native allocation type and streams with TMPDIR $mode"
      fi
    done
  done
  rm -rf -- "$scratch"
}
