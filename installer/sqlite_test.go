package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"testing"
)

func TestSQLiteReaderChecksProbeRows(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("POSIX fixture reader")
	}
	dir := t.TempDir()
	database := filepath.Join(dir, "SQLite probe.sqlite")
	cli := filepath.Join(dir, "sqlite3")
	script := `#!/bin/sh
[ "$1" = "-batch" ] && [ "$2" = "-init" ] && [ "$4" = "-readonly" ] && [ "$5" = "-json" ] || exit 2
[ -f "$6" ] || exit 3
case "$7" in *"WHERE probe MATCH 'vaultprobe'"*) ;; *) exit 4;; esac
printf '%s\n' "$VAULT_PROBE_ROWS"
`
	if err := os.WriteFile(cli, []byte(script), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(database, nil, 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", dir)
	t.Setenv("VAULT_PROBE_ROWS", `[{"body":"vaultprobe","test":1}]`)
	if got := findSQLite(database); got != cli {
		t.Fatalf("expected prepared reader %q, got %q", cli, got)
	}
	python := filepath.Join(dir, "fixture-python")
	if err := os.WriteFile(python, []byte("#!/bin/sh\n: > \"$5\"\n"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := prepareSQLite(python, dir); err != nil {
		t.Fatal(err)
	}
	recorded, err := os.ReadFile(filepath.Join(dir, "vault-sqlite3"))
	if err != nil || string(recorded) != cli+"\n" {
		t.Fatalf("recorded reader %q, error %v", recorded, err)
	}
	t.Setenv("VAULT_PROBE_ROWS", `[{"body":"vaultprobe","test":0}]`)
	if sqliteReadsProbe(cli, database) {
		t.Fatal("accepted a reader with the wrong probe result")
	}
}

func TestActualSQLiteWriterAndCLI(t *testing.T) {
	p := python()
	cli, err := exec.LookPath("sqlite3")
	if p == nil || err != nil {
		t.Skip("requires preinstalled Python and sqlite3")
	}
	database := filepath.Join(t.TempDir(), "probe.sqlite")
	args := append(append([]string{}, p[1:]...), "-I", "-S", "-c", sqliteWriterProbe, database)
	if out, err := exec.Command(p[0], args...).CombinedOutput(); err != nil {
		t.Skipf("preinstalled Python cannot write FTS5: %v %s", err, out)
	}
	if !sqliteReadsProbe(cli, database) {
		t.Skip("preinstalled sqlite3 is incompatible")
	}
}
