package main

import (
	"archive/zip"
	"bytes"
	"errors"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/Ridewarior/vault-framework"
)

type options struct {
	action, root, ref                   string
	tools, git, obsidian, hook, prepare bool
}

const usage = "Run vault for guided setup, or use vault {init|update|prepare} PATH [options]. Use vault init --help for command options."

func (o *options) flags() (*flag.FlagSet, error) {
	f := flag.NewFlagSet(o.action, flag.ContinueOnError)
	switch o.action {
	case "init":
		f.BoolVar(&o.obsidian, "obsidian", o.obsidian, "Include Obsidian settings")
		f.BoolVar(&o.git, "git", o.git, "Initialize a Git repository")
	case "update":
	case "prepare":
		f.BoolVar(&o.hook, "hook", o.hook, "Install the optional Git commit hooks")
	default:
		return nil, errors.New(usage)
	}
	if o.action != "prepare" {
		f.BoolVar(&o.tools, "tools", o.tools, "Include maintenance tools")
		f.StringVar(&o.ref, "ref", o.ref, "Fetch a GitHub branch, tag, or commit instead of using this binary's files")
	}
	return f, nil
}

func parse(args []string) (options, error) {
	o := options{action: args[0]}
	f, err := o.flags()
	if err != nil {
		return o, err
	}
	args = args[1:]
	if len(args) > 0 && !strings.HasPrefix(args[0], "-") {
		o.root, args = args[0], args[1:]
	}
	if err := f.Parse(args); err != nil {
		return o, err
	}
	if o.root == "" && f.NArg() == 1 {
		o.root = f.Arg(0)
	} else if o.root == "" || f.NArg() != 0 {
		return o, errors.New("supply one vault directory")
	}
	return o, nil
}

func source(ref string) (fs.FS, error) {
	if ref == "" {
		return vaultframework.Bundled, nil
	}
	client := http.Client{Timeout: 60 * time.Second}
	res, err := client.Get("https://api.github.com/repos/Ridewarior/vault-framework/zipball/" + url.PathEscape(ref))
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		return nil, fmt.Errorf("download %q: %s", ref, res.Status)
	}
	const limit = 32 << 20
	data, err := io.ReadAll(io.LimitReader(res.Body, limit+1))
	if err != nil {
		return nil, err
	}
	if len(data) > limit {
		return nil, errors.New("framework archive exceeds 32 MiB")
	}
	z, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
	if err != nil {
		return nil, err
	}
	entries, err := fs.ReadDir(z, ".")
	if err != nil {
		return nil, err
	}
	if len(entries) != 1 || !entries[0].IsDir() {
		return nil, errors.New("expected one repository in archive")
	}
	return fs.Sub(z, entries[0].Name())
}

func command(root string, args ...string) error {
	cmd := exec.Command(args[0], args[1:]...)
	cmd.Dir = root
	cmd.Env = []string{}
	for _, entry := range os.Environ() {
		key, _, _ := strings.Cut(entry, "=")
		switch strings.ToUpper(key) {
		case "GIT_DIR", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE":
			continue
		}
		cmd.Env = append(cmd.Env, entry)
	}
	cmd.Stdin, cmd.Stdout, cmd.Stderr = os.Stdin, os.Stdout, os.Stderr
	return cmd.Run()
}

const missingPython = "Python 3.10 or newer is required to run vault-tools. Install Python with venv support, then run vault prepare PATH."

func supportsPython(args []string) bool {
	probe := append(append([]string{}, args[1:]...), "-I", "-S", "-c", "import sys; sys.exit(sys.version_info < (3, 10))")
	cmd := exec.Command(args[0], probe...)
	// A version probe must not trigger the Windows Python manager to install a runtime.
	cmd.Env = append(os.Environ(), "PYTHON_MANAGER_AUTOMATIC_INSTALL=false")
	return cmd.Run() == nil
}
func python() []string {
	candidates := [][]string{{"python3"}, {"python"}}
	if runtime.GOOS == "windows" {
		candidates = append([][]string{{"py", "-3"}}, candidates...)
	}
	for _, candidate := range candidates {
		if supportsPython(candidate) {
			return candidate
		}
	}
	return nil
}
func prepareTools(o options) error {
	req := filepath.Join(o.root, "vault-tools", "requirements.txt")
	if _, err := os.Stat(req); err != nil {
		return fmt.Errorf("install the tools with vault update PATH --tools first: %w", err)
	}
	if o.hook {
		if _, err := exec.LookPath("git"); err != nil {
			return fmt.Errorf("Git is required for the hook: %w", err)
		}
		if _, err := os.Stat(filepath.Join(o.root, ".git")); err != nil {
			return fmt.Errorf("the hook needs a Git repository at the vault root: %w", err)
		}
	}
	env := filepath.Join(o.root, ".venv")
	interpreter := filepath.Join(env, "bin", "python")
	if runtime.GOOS == "windows" {
		interpreter = filepath.Join(env, "Scripts", "python.exe")
	}
	created := false
	if _, err := os.Lstat(env); os.IsNotExist(err) {
		p := python()
		if p == nil {
			return errors.New(missingPython)
		}
		if err := os.Mkdir(env, 0700); err != nil {
			return err
		}
		created = true
		if err := command(o.root, append(p, "-m", "venv", env)...); err != nil {
			return errors.Join(fmt.Errorf("create virtual environment: %w", err), os.RemoveAll(env))
		}
	} else if err != nil {
		return err
	}
	if _, err := os.Stat(filepath.Join(env, "pyvenv.cfg")); err != nil || !supportsPython([]string{interpreter}) {
		if created {
			return errors.Join(fmt.Errorf("could not create a usable Python 3.10+ environment at %s; rerun vault prepare after checking Python", env), os.RemoveAll(env))
		}
		return fmt.Errorf("invalid Python environment at %s; move that directory aside and rerun vault prepare %q", env, o.root)
	}
	if err := command(o.root, interpreter, "-m", "pip", "install", "-r", req); err != nil {
		return err
	}
	if o.hook {
		return command(o.root, interpreter, filepath.Join(o.root, "vault-tools", "vault.py"), "install-hook")
	}
	return nil
}

func vaultPath(path string) (string, error) {
	if strings.TrimSpace(path) == "" {
		return "", errors.New("enter a vault directory")
	}
	if path == "~" || strings.HasPrefix(filepath.ToSlash(path), "~/") {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		path = filepath.Join(home, strings.TrimPrefix(strings.TrimPrefix(filepath.ToSlash(path), "~"), "/"))
	}
	return filepath.Abs(path)
}

func execute(o options) error {
	root, err := vaultPath(o.root)
	if err != nil {
		return err
	}
	o.root = root
	if o.action == "prepare" {
		return prepareTools(o)
	}
	src, err := source(o.ref)
	if err != nil {
		return err
	}
	if o.action == "init" {
		err = createVault(src, o)
	} else {
		err = updateVault(src, o)
	}
	if err != nil {
		return err
	}
	if o.prepare {
		return prepareTools(o)
	}
	return nil
}
func main() {
	args := os.Args[1:]
	if len(args) == 1 {
		switch args[0] {
		case "--help", "-h", "help":
			fmt.Println(usage)
			return
		case "--version":
			v, _ := vaultframework.Bundled.ReadFile("framework/VERSION")
			fmt.Print(string(v))
			return
		}
	}
	var o options
	var err error
	if len(args) == 0 {
		o, err = wizard(os.Stdin, os.Stdout)
	} else {
		o, err = parse(args)
		if err == nil && o.tools && python() == nil {
			fmt.Fprintln(os.Stderr, missingPython)
		}
	}
	if errors.Is(err, flag.ErrHelp) {
		return
	}
	if err == nil && o.action != "" {
		err = execute(o)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "vault:", err)
		os.Exit(1)
	}
}
