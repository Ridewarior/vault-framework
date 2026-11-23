package main

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
)

func copyDir(src fs.FS, name, dest string) error {
	info, err := fs.Stat(src, name)
	if err != nil {
		return err
	}
	if !info.IsDir() {
		return fmt.Errorf("expected directory %s", name)
	}
	tree, err := fs.Sub(src, name)
	if err != nil {
		return err
	}
	return os.CopyFS(dest, tree)
}

func installShared(src fs.FS, stage, name string) error {
	dir := "framework"
	required := []string{"VERSION", "README.md", "organization.md", "notes.md"}
	if name == "vault-tools" {
		dir = "tools"
		required = []string{"vault.py", "requirements.txt", "README.md"}
	}
	if _, err := fs.Stat(src, dir); errors.Is(err, fs.ErrNotExist) {
		dir = name
	}
	for _, file := range required {
		info, err := fs.Stat(src, dir+"/"+file)
		if err != nil {
			return err
		}
		if !info.Mode().IsRegular() {
			return fmt.Errorf("invalid %s/%s", dir, file)
		}
	}
	dest := filepath.Join(stage, name)
	if err := copyDir(src, dir, dest); err != nil {
		return err
	}
	if name != "vault-tools" {
		return nil
	}
	// Older revisions included the skill in the tools directory, if present.
	skill := "skills/discover-vault"
	if _, err := fs.Stat(src, skill); errors.Is(err, fs.ErrNotExist) {
		return nil
	} else if err != nil {
		return err
	}
	return copyDir(src, skill, filepath.Join(dest, filepath.FromSlash(skill)))
}

// checkDestination returns true if the destination is an existing empty directory.
func checkDestination(root string) (bool, error) {
	info, err := os.Lstat(root)
	if os.IsNotExist(err) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return false, fmt.Errorf("%q is a symbolic link. Enter the path to a new or empty folder", root)
	}
	if !info.IsDir() {
		return false, fmt.Errorf("%q is not a directory. Enter the path to a new or empty folder", root)
	}
	files, err := os.ReadDir(root)
	if err != nil {
		return false, err
	}
	if len(files) > 0 {
		return false, fmt.Errorf("%q already contains files or folders. Choose an empty folder or enter a new path such as %q", root, filepath.Join(root, "My Vault"))
	}
	return true, nil
}

func createVault(src fs.FS, o options) error {
	root := o.root
	existing, err := checkDestination(root)
	if err != nil {
		return err
	}
	parent := filepath.Dir(root)
	if err := os.MkdirAll(parent, 0755); err != nil {
		return err
	}
	if existing {
		parent = root
	}
	stage, err := os.MkdirTemp(parent, ".vault-setup-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(stage)
	for _, dir := range []string{"templates", "inbox", "guidelines"} {
		if err := copyDir(src, "starter/"+dir, filepath.Join(stage, dir)); err != nil {
			return err
		}
	}
	if o.obsidian {
		if err := copyDir(src, "starter/.obsidian", filepath.Join(stage, ".obsidian")); err != nil {
			return err
		}
	}
	files := []string{"starter/AGENTS.md", "starter/README.md", "starter/vault.config.json"}
	if o.git {
		files = append(files, ".gitignore", ".gitattributes")
	}
	for _, name := range files {
		data, err := fs.ReadFile(src, name)
		if err != nil {
			return err
		}
		if err = os.WriteFile(filepath.Join(stage, filepath.Base(name)), data, 0644); err != nil {
			return err
		}
	}
	if err := installShared(src, stage, "vault-framework"); err != nil {
		return err
	}
	if o.tools {
		if err := installShared(src, stage, "vault-tools"); err != nil {
			return err
		}
	}
	if o.git {
		if err := command(stage, "git", "init", "--quiet"); err != nil {
			return err
		}
	}
	if existing {
		err = populateExisting(stage, root)
	} else {
		err = os.Rename(stage, root)
	}
	if err != nil {
		return err
	}
	fmt.Println("Created vault at", root)
	return nil
}

// Keep the directory itself, including its permissions and any shell using it.
// Claim each new path exclusively so a late collision can be rolled back safely.
func populateExisting(stage, root string) error {
	var created []string
	err := filepath.WalkDir(stage, func(src string, entry fs.DirEntry, err error) error {
		if err != nil || src == stage {
			return err
		}
		rel, err := filepath.Rel(stage, src)
		if err != nil {
			return err
		}
		dest := filepath.Join(root, rel)
		info, err := entry.Info()
		if err != nil {
			return err
		}
		switch {
		case entry.IsDir():
			err = os.Mkdir(dest, info.Mode().Perm())
		case entry.Type()&os.ModeSymlink != 0:
			var link string
			link, err = os.Readlink(src)
			if err == nil {
				err = os.Symlink(link, dest)
			}
		case entry.Type().IsRegular():
			input, err := os.Open(src)
			if err != nil {
				return err
			}
			defer input.Close()
			output, err := os.OpenFile(dest, os.O_CREATE|os.O_EXCL|os.O_WRONLY, info.Mode().Perm())
			if err != nil {
				return err
			}
			created = append(created, dest)
			_, err = io.Copy(output, input)
			return errors.Join(err, output.Close())
		default:
			return fmt.Errorf("unsupported starter file %s", rel)
		}
		if err == nil {
			created = append(created, dest)
		}
		return err
	})
	if err != nil {
		for i := len(created) - 1; i >= 0; i-- {
			err = errors.Join(err, os.Remove(created[i]))
		}
	}
	return err
}

func sameTree(a, b string) (bool, error) {
	left, err := os.ReadDir(a)
	if os.IsNotExist(err) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	right, err := os.ReadDir(b)
	if err != nil {
		return false, err
	}
	if len(left) != len(right) {
		return false, nil
	}
	for i, x := range left {
		y := right[i]
		if x.Name() != y.Name() || x.Type() != y.Type() {
			return false, nil
		}
		old, newFile := filepath.Join(a, x.Name()), filepath.Join(b, y.Name())
		if x.IsDir() {
			same, err := sameTree(old, newFile)
			if !same || err != nil {
				return same, err
			}
			continue
		}
		if !x.Type().IsRegular() {
			return false, nil
		}
		first, err := os.ReadFile(old)
		if err != nil {
			return false, err
		}
		second, err := os.ReadFile(newFile)
		if err != nil {
			return false, err
		}
		if !bytes.Equal(first, second) {
			return false, nil
		}
	}
	return true, nil
}

func updateVault(src fs.FS, o options) error {
	root := o.root
	lock := filepath.Join(root, ".vault-update-lock")
	if err := os.Mkdir(lock, 0700); err != nil {
		return fmt.Errorf("acquire update lock: %w", err)
	}
	defer os.Remove(lock)
	names := []string{"vault-framework"}
	tools := filepath.Join(root, "vault-tools")
	if _, err := os.Lstat(tools); err == nil || o.tools {
		names = append(names, "vault-tools")
	} else if !os.IsNotExist(err) {
		return err
	}
	for _, name := range names {
		info, err := os.Lstat(filepath.Join(root, name))
		if os.IsNotExist(err) && name == "vault-tools" {
			continue
		}
		if err != nil {
			return err
		}
		if !info.IsDir() {
			return fmt.Errorf("expected an ordinary directory at %s", name)
		}
	}
	if info, err := os.Lstat(filepath.Join(root, "vault-framework", "VERSION")); err != nil || !info.Mode().IsRegular() {
		return errors.New("expected an installed vault-framework/VERSION")
	}
	work, err := os.MkdirTemp(root, ".vault-update-")
	if err != nil {
		return err
	}
	keep := false
	defer func() {
		if !keep {
			os.RemoveAll(work)
		}
	}()
	if err := os.WriteFile(filepath.Join(work, ".gitignore"), []byte("*\n"), 0600); err != nil {
		return err
	}
	previous := filepath.Join(work, "previous")
	if err := os.Mkdir(previous, 0700); err != nil {
		return err
	}
	var changes []string
	for _, name := range names {
		if err := installShared(src, work, name); err != nil {
			return err
		}
		same, err := sameTree(filepath.Join(root, name), filepath.Join(work, name))
		if err != nil {
			return err
		}
		if !same {
			changes = append(changes, name)
		}
	}
	if len(changes) == 0 {
		fmt.Println("Shared files are current.")
		return nil
	}
	type move struct{ from, to string }
	var moves []move
	rename := func(from, to string) error {
		err := os.Rename(from, to)
		if err == nil {
			moves = append(moves, move{from, to})
		}
		return err
	}
	for _, name := range changes {
		current := filepath.Join(root, name)
		if _, err = os.Lstat(current); err == nil {
			err = rename(current, filepath.Join(previous, name))
			if err != nil {
				break
			}
			keep = true
		} else if !os.IsNotExist(err) {
			break
		}
		err = rename(filepath.Join(work, name), current)
		if err != nil {
			break
		}
	}
	if err != nil {
		for i := len(moves) - 1; i >= 0; i-- {
			m := moves[i]
			if undo := os.Rename(m.to, m.from); undo != nil {
				keep = true
				return fmt.Errorf("update failed (%v); recover files from %s: %w", err, work, undo)
			}
		}
		keep = false
		return err
	}
	fmt.Println("Updated", changes)
	for _, name := range names {
		os.RemoveAll(filepath.Join(work, name))
	}
	if keep {
		fmt.Println("Previous files:", previous)
	}
	return nil
}
