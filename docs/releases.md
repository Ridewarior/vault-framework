# Publish a vault release

A Git tag names the commit you want to distribute. A GitHub release gives that tag a download page. Our workflow builds the executables and attaches them to a draft. You choose when to publish it. [GitHub release guide](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)

1. Commit and push the wizard and workflow to the default branch. To rehearse, open **Actions → Build vault release → Run workflow**. A manual run tests the Go CLI on Linux, macOS, and Windows, then builds downloadable artifacts. You can download the artifact from the run page.
2. Choose the framework version. For a first trial, one possible value is `0.1.0-rc.1`. Put the chosen value in `framework/VERSION`, commit it, and push. Run `go test ./...` and the Python tests before tagging. Review the commit with `git show --stat HEAD`.
3. Tag that commit and push the tag. For the example version, run `git tag -a v0.1.0-rc.1 -m "First vault wizard trial"`, then `git push origin v0.1.0-rc.1`. The tag must match the version file with a leading `v`.
4. Open **Actions → Build vault release**. When it finishes, open **Releases** and edit the draft. Check the notes, the six binaries, the Unix launcher, and `SHA256SUMS`. Download the binary for your machine and try it with an empty directory. If the workflow fails, open the failed step in Actions. A common cause at the draft step is a tag that differs from the version file.
5. For a trial, select **Set as a pre-release**. For a regular release you want the launcher to download, select **Set as the latest release**. Click **Publish release**. The first regular release marked latest enables the one-line commands in the [setup guide](setup.md). To try an earlier or prerelease binary, use its tagged download page. [How latest download links work](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases)

Builds cover Intel/AMD 64-bit and ARM64 machines. The binaries are unsigned. To build the same downloads locally on Linux with Go and sha256sum, run `sh scripts/build-release.sh /tmp/vault-downloads`.
