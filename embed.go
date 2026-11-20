package vaultframework

import "embed"

// Bundled contains the files shipped with the vault installer.
//
//go:embed framework/*.md framework/VERSION starter/*.md starter/*.json starter/guidelines/*.md starter/templates/*.md starter/inbox/.gitkeep starter/.obsidian/app.json starter/.obsidian/community-plugins.json starter/.obsidian/core-plugins.json starter/.obsidian/templates.json starter/.obsidian/types.json tools/vault.py tools/requirements.txt tools/README.md .gitignore .gitattributes
var Bundled embed.FS
