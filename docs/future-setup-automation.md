# Future setup automation

Setup automation is deferred. [Manual copying and dependency setup](manual-setup.md) are enough for now.

An earlier draft tried a Bash entry point for creating vaults, preparing devices, and cloning existing vaults. Revisit it only if repeated manual setup becomes a problem.

Any future approach should respect the current design:

- Vaults choose their storage. Git is one option.
- The framework goes in `vault-framework/`. Editable vault rules go in `guidelines/`.
- Getting a framework copy is separate from note upkeep and should not happen during normal agent startup or commits.
- Device setup should preserve notes, local rules, templates, and the chosen framework version.
- Dependency installation should be explicit and supported on the owner's actual devices.

The retired prototype tested temporary Python environments, local source copies, selected Git revisions, and repeated setup. System package installation and other operating systems were not verified. Those ideas would need fresh testing if revived.
