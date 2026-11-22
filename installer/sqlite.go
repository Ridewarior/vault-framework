package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

const sqliteWriterProbe = `
import sqlite3
import sys
from contextlib import closing

with closing(sqlite3.connect(sys.argv[1])) as db, db:
    db.execute("CREATE VIRTUAL TABLE probe USING fts5(body)")
    db.execute("INSERT INTO probe VALUES ('vaultprobe')")
    if db.execute("SELECT body FROM probe WHERE probe MATCH 'vaultprobe'").fetchone() != ("vaultprobe",):
        sys.exit("SQLite FTS5 did not return the probe row")
`

func prepareSQLite(interpreter, environment string) error {
	temp, err := os.MkdirTemp("", "vault-sqlite-probe-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(temp)
	database := filepath.Join(temp, "probe.sqlite")
	writer := exec.Command(interpreter, "-I", "-S", "-c", sqliteWriterProbe, database)
	writer.Dir = temp
	if output, err := writer.CombinedOutput(); err != nil {
		return fmt.Errorf("Python cannot write an FTS5 catalog. Use a Python build with SQLite FTS5: %w\n%s", err, output)
	}

	reader := findSQLite(database)
	if reader == "" {
		install := sqliteInstallCommand()
		if len(install) == 0 {
			return errors.New("install a compatible sqlite3 CLI with FTS5 and JSON support, put it on PATH, and rerun vault prepare")
		}
		fmt.Printf("Installing sqlite3 with %s.\n", strings.Join(install, " "))
		if err := command(temp, install...); err != nil {
			return fmt.Errorf("install sqlite3: %w. Install a compatible CLI, put it on PATH, and rerun vault prepare", err)
		}
		reader = findSQLite(database)
		if reader == "" {
			return errors.New("sqlite3 could not read the FTS5 probe in read-only JSON mode. Put a compatible CLI on PATH and rerun vault prepare")
		}
	}
	reader, err = filepath.Abs(reader)
	if err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(environment, "vault-sqlite3"), []byte(reader+"\n"), 0600); err != nil {
		return fmt.Errorf("record the verified sqlite3 reader: %w", err)
	}
	fmt.Printf("SQLite catalog writer and reader checked. Use %q for catalog queries.\n", reader)
	return nil
}

func findSQLite(database string) string {
	if cli, err := exec.LookPath("sqlite3"); err == nil && sqliteReadsProbe(cli, database) {
		return cli
	}
	var alternate string
	switch runtime.GOOS {
	case "darwin":
		// Homebrew's formula can be keg-only, leaving the system binary on PATH.
		brew := exec.Command("brew", "--prefix", "sqlite")
		brew.Dir = filepath.Dir(database)
		if out, err := brew.Output(); err == nil {
			alternate = filepath.Join(strings.TrimSpace(string(out)), "bin", "sqlite3")
		}
	case "windows":
		if local := os.Getenv("LOCALAPPDATA"); local != "" {
			alternate = filepath.Join(local, "Microsoft", "WinGet", "Links", "sqlite3.exe")
		}
	}
	if filepath.IsAbs(alternate) && sqliteReadsProbe(alternate, database) {
		return alternate
	}
	return ""
}

func sqliteReadsProbe(cli, database string) bool {
	query := "SELECT body, json_extract('{\"test\":1}', '$.test') AS test FROM probe WHERE probe MATCH 'vaultprobe'"
	probe := exec.Command(cli, "-batch", "-init", os.DevNull, "-readonly", "-json", database, query)
	probe.Dir = filepath.Dir(database)
	out, err := probe.Output()
	if err != nil {
		return false
	}
	var rows []struct {
		Body string
		Test int
	}
	return json.Unmarshal(out, &rows) == nil && len(rows) == 1 && rows[0].Body == "vaultprobe" && rows[0].Test == 1
}

func sqliteInstallCommand() []string {
	var candidates [][]string
	switch runtime.GOOS {
	case "darwin":
		candidates = [][]string{{"brew", "install", "sqlite"}}
	case "windows":
		candidates = [][]string{{"winget", "install", "--id", "SQLite.SQLite", "--exact", "--source", "winget", "--scope", "user"}}
	case "linux":
		candidates = [][]string{
			{"apt-get", "install", "sqlite3"},
			{"dnf", "install", "sqlite"},
			{"pacman", "-S", "sqlite"},
			{"zypper", "install", "sqlite3"},
		}
	}
	for _, candidate := range candidates {
		if _, err := exec.LookPath(candidate[0]); err != nil {
			continue
		}
		if runtime.GOOS == "linux" && os.Geteuid() != 0 {
			if _, err := exec.LookPath("sudo"); err != nil {
				return nil
			}
			return append([]string{"sudo"}, candidate...)
		}
		return candidate
	}
	return nil
}
