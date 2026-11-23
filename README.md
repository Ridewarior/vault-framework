# Vault framework

Vault framework helps you and your agents keep a shared collection of Markdown notes. Use a vault to record why you made a decision, find the evidence behind it, or pick up work where you left off. The installer creates the folder structure, note templates, and guidelines. You choose how to organize, store, and sync your notes.

## Get started

On Linux with an x86-64 processor, download the published prerelease and start the setup wizard with one command:

```sh
curl -fL https://github.com/Ridewarior/vault-framework/releases/download/v0.1.0-draft/vault-linux-amd64 -o vault && chmod +x vault && ./vault
```

Choose **Create a vault** and give it a new or empty folder. The wizard offers Obsidian settings, Git, and search tools as optional additions.

For macOS, Windows, or ARM64 Linux, download the executable for your platform from the [release page](https://github.com/Ridewarior/vault-framework/releases). To try the version in this checkout with Go 1.23 or newer, run `go run ./installer`. The [setup guide](docs/setup.md) covers command-line options and updates.

## Inside a vault

The installer puts the shared rules in `vault-framework/`. Use `guidelines/` for your vault's tags and workflows, and `AGENTS.md` to tell agents how to work with your notes. Updating the framework replaces the shared files and preserves your local rules.

| Guide | What you'll find |
| --- | --- |
| [Framework](framework/README.md) | How to organize notes, link evidence, and record decisions |
| [Starter](starter/README.md) | The guidelines, inbox, and templates for a new vault |
| [Examples](examples/README.md) | A personal vault and a work vault with ticket notes |
| [Maintenance tools](tools/README.md) | SQLite search and optional Git hooks |
| [Agent skills](skills) | Setup instructions and queries for finding notes |
| [Releases](docs/releases.md) | How versions are built and published |
