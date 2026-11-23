package vaultframework

import "embed"

// Bundled contains the files shipped with the vault installer.
//
//go:embed framework/*.md framework/VERSION framework/CATALOG_SCHEMA_VERSION starter/*.md starter/guidelines/*.md starter/templates/*.md starter/inbox/.gitkeep starter/.obsidian/app.json starter/.obsidian/community-plugins.json starter/.obsidian/core-plugins.json starter/.obsidian/templates.json starter/.obsidian/types.json tools/*.py tools/requirements.txt tools/README.md skills/discover-vault .gitignore .gitattributes
var Bundled embed.FS
