# Set up a vault

Run the vault executable with no arguments for a guided walkthrough. It can create a vault, update the shared folders, or prepare maintenance tools on a new device. The executable includes the starter, framework, and Python tool files for its version.

## Launch the wizard

From the repository root with Go 1.23 or newer, run `go run ./installer`. To keep the executable, run `go build -o vault ./installer` on Linux or macOS, or `go build -o vault.exe ./installer` on Windows.

The [installer folder](../installer/) holds the command, tests, and release scripts. Go embeds files relative to their package, so the [embed declaration](../embed.go) lives at the root alongside the files it bundles.

Once a release is published as latest, run this on Linux or macOS with curl:

```sh
curl -fsSL https://github.com/Ridewarior/vault-framework/releases/latest/download/launch-vault.sh -o launch-vault.sh && sh launch-vault.sh
```

The launcher downloads the executable for this machine into a temporary directory and starts it with your terminal attached. It accepts the same arguments as the executable.

On Windows, run this in PowerShell:

```powershell
$arch = @{ X64 = 'amd64'; Arm64 = 'arm64' }[[Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()]; if (!$arch) { throw "Unsupported processor" }; Invoke-WebRequest "https://github.com/Ridewarior/vault-framework/releases/latest/download/vault-windows-$arch.exe" -OutFile vault.exe -ErrorAction Stop; .\vault.exe
```

You can also download the executable directly from the release page. On Unix, give it execute permission with `chmod +x`. For a prerelease, use its tagged release page. See [publishing releases](releases.md).

## Use commands directly

Use these examples with a binary named `vault` in your PATH, or substitute its path.

```sh
vault init "/path/to/My Vault" --obsidian --tools --git
vault prepare "/path/to/My Vault" --hook
vault update "/path/to/My Vault"
```

`init` takes a new or empty directory. All three flags are optional. Git is needed for `--git`. Copying tools works even if Python is missing. The [work example](../examples/work/README.md) has additional rules and templates. You can also [copy the starter by hand](manual-setup.md).

`prepare` uses Python 3.10 or newer with venv support. It creates or reuses the vault's local `.venv/` and installs PyYAML there. Run it on each device that uses the tools. If a previous run left an invalid `.venv/`, move it aside and rerun `prepare`. For a Git vault, `--hook` installs the vault commit hooks. Stage `vault.config.json` before the first commit. Exclude virtual environments from sync.

`update` uses the framework bundled in the executable. Download a newer binary or rerun the launcher to update to a published version. To fetch a specific source revision, use `--ref TAG_OR_COMMIT` with init or update. Update replaces the shared folders, backs up their previous contents in `.vault-update-*/previous/`, and prints the backup path. Add `--tools` to install tools in an existing vault. After an interrupted update, check that both shared folders are complete, restore any missing copies from the backup, then remove a leftover `.vault-update-lock` once the updater has stopped.

For agent-assisted setup, give the agent the [setup skill](../skills/setup-vault/SKILL.md), a destination, and a short description of what the vault is for. The skill uses the direct commands and adapts the installed README, guidelines, and agent instructions to your brief.
