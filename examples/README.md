# Examples

These examples use invented notes, dates, and ticket identifiers. They do not represent real approvals or test results.

The personal example shows references, research, a decision, and inbox captures. The [work example](work/README.md) adds local ticket rules and templates. Adopt only what fits a vault.

Follow [manual setup](../docs/manual-setup.md) to assemble a vault, then copy any example material you want to try. These directories are examples within the framework repository, not separate vault repositories.

Each includes an index configuration. Regenerate the sample indexes with:

```sh
python vault-tools/vault.py --vault examples/personal index
python vault-tools/vault.py --vault examples/work index
```

The generated indexes show paths and subdirectory sections. Inbox notes are omitted so the examples also demonstrate direct capture without metadata.
