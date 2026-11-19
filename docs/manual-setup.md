# Manual vault setup

Download or clone the [framework repository](https://github.com/Ridewarior/vault-framework). Choose where the vault will live and how it will be stored or synced. Git is optional.

## Copy the starter

Use this guide to copy files by hand. The repository also has a [setup command](setup.md).

Use a new, empty directory. From the downloaded repository, copy:

| Source | Destination |
| --- | --- |
| `starter/AGENTS.md`, `starter/README.md`, `starter/vault.config.json` | Vault root |
| `starter/inbox/` | `inbox/` |
| `starter/guidelines/` | `guidelines/`, the vault's editable rules |
| `starter/templates/` | `templates/` |
| `framework/` | `vault-framework/`, the framework copy |

For example, from a Unix-like shell:

```sh
vault_dir=/path/to/new-vault
mkdir -p "$vault_dir"
cp starter/AGENTS.md starter/README.md starter/vault.config.json "$vault_dir/"
cp -R starter/inbox "$vault_dir/inbox"
cp -R starter/guidelines "$vault_dir/guidelines"
cp -R starter/templates "$vault_dir/templates"
cp -R framework "$vault_dir/vault-framework"
```

Edit the vault README, local guidelines, and agent instructions for its purpose. Keep `vault-framework/` unchanged. These commands assume an empty destination; review existing files before copying an update over them.

## Optional additions

For Obsidian settings:

```sh
cp -R starter/.obsidian "$vault_dir/.obsidian"
```

For the Python index tool and its guide:

```sh
cp -R tools "$vault_dir/vault-tools"
```

Install Python and PyYAML as described in the tool guide. Index generation works without Git. Keep virtual environments out of the vault's sync or sharing rules where needed.

For a vault using Git:

```sh
cp .gitignore .gitattributes "$vault_dir/"
git init "$vault_dir"
```

The Git hook is an optional step described in the copied tool guide. Keep this repository's own `.git/` directory out of the vault.

The [work example](../examples/work/README.md) provides ticket rules and templates for a vault that needs them. They are not required for a personal vault.

## Framework versions and other devices

Every framework copy includes `vault-framework/VERSION`. Copy the whole folder so its version stays with its contents. Review a new framework version before replacing that folder, and keep local rules in root or scoped `guidelines/`.

If an exact source commit or unpublished draft needs recording, add that detail to the vault README. Leave the framework's version file unchanged in the vault.

On another device, obtain the existing vault through its chosen storage method. Repeat local tool setup if needed.
