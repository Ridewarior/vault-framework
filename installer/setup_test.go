package main

import (
	"bytes"
	"io/fs"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/Ridewarior/vault-framework"
)

func TestWizardAndAgentCreateSameVault(t *testing.T) {
	t.Setenv("PATH", t.TempDir()) // Fresh machine with neither Python nor Git.
	first := filepath.Join(t.TempDir(), "My Vault")
	var output bytes.Buffer
	answers := "1\n" + first + "\ny\nn\ny\ny\n"
	o, err := wizard(strings.NewReader(answers), &output)
	if err != nil || !strings.Contains(output.String(), "3.10") {
		t.Fatalf("wizard: %v %s", err, output.String())
	}
	if err = execute(o); err != nil {
		t.Fatal(err)
	}
	second := t.TempDir()
	agent, err := parse([]string{"init", second, "--obsidian", "--tools"})
	if err != nil {
		t.Fatal(err)
	}
	if err = execute(agent); err != nil {
		t.Fatal(err)
	}
	if same, err := sameTree(first, second); err != nil || !same {
		t.Fatal("installations differ", err)
	}
	for _, name := range []string{"vault-framework/VERSION", "vault-tools/vault.py", "guidelines/README.md", ".obsidian/templates.json", "inbox/.gitkeep"} {
		if _, err := os.Stat(filepath.Join(first, name)); err != nil {
			t.Fatal(err)
		}
	}
	if err := prepareTools(options{root: first}); err == nil || !strings.Contains(err.Error(), "3.10") {
		t.Fatal("missing Python:", err)
	}
	if _, err := os.Stat(filepath.Join(first, ".venv")); !os.IsNotExist(err) {
		t.Fatal("partially installed environment")
	}
	if err := execute(o); err == nil {
		t.Fatal("overwrote existing vault")
	}
}

func TestCancellation(t *testing.T) {
	var out bytes.Buffer
	o, err := wizard(strings.NewReader("2\nsome vault\nn\nn\n"), &out)
	if err != nil || o.action != "" {
		t.Fatal("cancel:", o, err)
	}
}

func TestWizardRetriesNonemptyDestinationBeforeAskingOptions(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("USERPROFILE", home)
	docs := filepath.Join(home, "Documents")
	if err := os.Mkdir(docs, 0755); err != nil {
		t.Fatal(err)
	}
	note := filepath.Join(docs, "notes.md")
	if err := os.WriteFile(note, []byte("keep this"), 0644); err != nil {
		t.Fatal(err)
	}
	var out bytes.Buffer
	answers := "1\n~/Documents\n~/Documents/My Vault\nn\nn\nn\ny\n"
	o, err := wizard(strings.NewReader(answers), &out)
	if err != nil {
		t.Fatal(err)
	}
	firstPrompt, options, found := strings.Cut(out.String(), "Include Obsidian settings?")
	if !found || options == "" || strings.Count(firstPrompt, "Vault directory:") != 2 ||
		!strings.Contains(firstPrompt, "already contains files or folders") {
		t.Fatalf("unexpected wizard flow: %s", out.String())
	}
	if o.root != filepath.Join(docs, "My Vault") {
		t.Fatalf("unexpected destination %q", o.root)
	}
	if err := execute(o); err != nil {
		t.Fatal(err)
	}
	if data, err := os.ReadFile(note); err != nil || string(data) != "keep this" {
		t.Fatal("existing note changed", err)
	}
}

func TestUpdatePreviousLayoutAndBackup(t *testing.T) {
	root := t.TempDir()
	if err := createVault(vaultframework.Bundled, options{root: root}); err != nil {
		t.Fatal(err)
	}
	rules := filepath.Join(root, "guidelines", "README.md")
	if err := os.WriteFile(rules, []byte("local rules"), 0644); err != nil {
		t.Fatal(err)
	}
	oldVersion, err := os.ReadFile(filepath.Join(root, "vault-framework/VERSION"))
	if err != nil {
		t.Fatal(err)
	}
	// Tagged revisions before the repo rename used the installed directory names.
	src := fstest.MapFS{}
	for _, name := range []string{"vault-framework/README.md", "vault-framework/VERSION", "vault-framework/notes.md", "vault-framework/organization.md", "vault-tools/README.md", "vault-tools/requirements.txt", "vault-tools/vault.py"} {
		src[name] = &fstest.MapFile{Data: []byte("new revision")}
	}
	o := options{root: root, tools: true}
	delete(src, "vault-tools/vault.py")
	if err := updateVault(src, o); err == nil {
		t.Fatal("accepted incomplete source")
	}
	current, err := os.ReadFile(filepath.Join(root, "vault-framework/VERSION"))
	if err != nil || !bytes.Equal(current, oldVersion) {
		t.Fatal("partial update", err)
	}
	src["vault-tools/vault.py"] = &fstest.MapFile{Data: []byte("tool")}
	for _, guide := range []string{"notes.md", "organization.md"} {
		path := "vault-framework/" + guide
		saved := src[path]
		delete(src, path)
		if err := updateVault(src, o); err == nil {
			t.Fatalf("accepted framework without %s", guide)
		}
		current, err := os.ReadFile(filepath.Join(root, "vault-framework/VERSION"))
		if err != nil || !bytes.Equal(current, oldVersion) {
			t.Fatal("incomplete revision replaced installed framework", err)
		}
		src[path] = saved
	}
	for i := 0; i < 2; i++ {
		if err := updateVault(src, o); err != nil {
			t.Fatal(err)
		}
	}
	backups, err := filepath.Glob(filepath.Join(root, ".vault-update-*", "previous", "vault-framework", "VERSION"))
	if err != nil || len(backups) != 1 {
		t.Fatal(backups, err)
	}
	saved, err := os.ReadFile(backups[0])
	if err != nil || !bytes.Equal(saved, oldVersion) {
		t.Fatal("backup:", err)
	}
	if body, err := os.ReadFile(rules); err != nil || string(body) != "local rules" {
		t.Fatal("local rules changed", err)
	}
	for _, name := range []string{"vault-tools/vault.py", "vault-framework/VERSION"} {
		got, err := os.ReadFile(filepath.Join(root, name))
		want, _ := fs.ReadFile(src, name)
		if err != nil || !bytes.Equal(got, want) {
			t.Fatal(name, err)
		}
	}
}

func TestInitKeepsExistingDirectory(t *testing.T) {
	root := t.TempDir()
	if err := os.Chmod(root, 0750); err != nil {
		t.Fatal(err)
	}
	before, err := os.Stat(root)
	if err != nil {
		t.Fatal(err)
	}
	if err := createVault(vaultframework.Bundled, options{root: root}); err != nil {
		t.Fatal(err)
	}
	after, err := os.Stat(root)
	if err != nil {
		t.Fatal(err)
	}
	if !os.SameFile(before, after) || before.Mode() != after.Mode() {
		t.Fatalf("init replaced or changed mode of %s", root)
	}
	if _, err := os.Stat(filepath.Join(root, "vault-framework", "VERSION")); err != nil {
		t.Fatal(err)
	}
}

func TestPopulateExistingRollsBackCollision(t *testing.T) {
	root, stage := t.TempDir(), t.TempDir()
	for _, name := range []string{"a", "b"} {
		if err := os.WriteFile(filepath.Join(stage, name), []byte("new"), 0644); err != nil {
			t.Fatal(err)
		}
	}
	old := filepath.Join(root, "b")
	if err := os.WriteFile(old, []byte("original"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := populateExisting(stage, root); err == nil {
		t.Fatal("accepted collision")
	}
	if _, err := os.Stat(filepath.Join(root, "a")); !os.IsNotExist(err) {
		t.Fatal("left partial install", err)
	}
	if data, err := os.ReadFile(old); err != nil || string(data) != "original" {
		t.Fatal("overwrote existing file", err)
	}
}

func TestPreparePreservesPreexistingInvalidEnvironment(t *testing.T) {
	root := t.TempDir()
	o := options{root: root, tools: true}
	if err := createVault(vaultframework.Bundled, o); err != nil {
		t.Fatal(err)
	}
	env := filepath.Join(root, ".venv")
	if err := os.Mkdir(env, 0700); err != nil {
		t.Fatal(err)
	}
	marker := filepath.Join(env, "existing")
	if err := os.WriteFile(marker, []byte("keep"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := prepareTools(o); err == nil || !strings.Contains(err.Error(), "move that directory aside") {
		t.Fatal("missing recovery guidance", err)
	}
	if _, err := os.Stat(marker); err != nil {
		t.Fatal(err)
	}
}

func TestPrepareRetriesAfterFailedCreation(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("POSIX fixture interpreter")
	}
	root, bin := t.TempDir(), t.TempDir()
	o := options{root: root, tools: true}
	if err := createVault(vaultframework.Bundled, o); err != nil {
		t.Fatal(err)
	}
	fake := "#!/bin/sh\ncase $1 in -I) exit 0;; -m) echo partial > \"$3/pyvenv.cfg\"; exit 1;; esac\nexit 2\n"
	if err := os.WriteFile(filepath.Join(bin, "python3"), []byte(fake), 0755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", bin)
	for i := 0; i < 2; i++ {
		if err := prepareTools(o); err == nil || !strings.Contains(err.Error(), "create virtual environment") {
			t.Fatal(err)
		}
		if _, err := os.Stat(filepath.Join(root, ".venv")); !os.IsNotExist(err) {
			t.Fatal("left incomplete environment", err)
		}
	}
}

func TestWizardPreviewMatchesCLI(t *testing.T) {
	for _, args := range [][]string{{"init", "myvault", "--tools", "--obsidian", "--git"}, {"prepare", "myvault", "--hook"}, {"update", "myvault", "--tools", "--ref", "main"}} {
		o, err := parse(args)
		if err != nil {
			t.Fatal(err)
		}
		words := strings.Fields(o.preview())
		for i, w := range words {
			if quoted, e := strconv.Unquote(w); e == nil {
				words[i] = quoted
			}
		}
		got, err := parse(words[1:])
		if err != nil || got != o {
			t.Fatalf("preview %q: got %+v, want %+v: %v", o.preview(), got, o, err)
		}
	}
}
