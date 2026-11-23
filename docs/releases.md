# Publish a vault release

A Git tag names the commit you want to distribute. A GitHub release gives that tag a download page. `Ridewarior` can rehearse a build from a candidate branch, creates release drafts from `main`, and decides when to publish. [GitHub release guide](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)

## Set up release approval

In **Settings → Environments**, create an environment named `release`. Set `Ridewarior` as its sole required reviewer. Leave **Prevent self-review** off so the same account can start and approve a run. Turn off **Allow administrators to bypass configured protection rules**. Under **Deployment branches and tags**, choose **Selected branches and tags** and add `main` as a **Branch** rule. [GitHub environment guide](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)

## Build and publish

1. For a release draft, choose an unused version in [framework/VERSION](../framework/VERSION). For a trial, use a suffix such as `-rc.1`. If the version needs changing, open a pull request and merge it after the checks pass.
2. Open **Actions → Build vault release → Run workflow** and select the branch to test. Leave **Create a draft release after building the downloads** unchecked for a rehearsal. The workflow tests the Go command on Linux, macOS, and Windows. When it finishes, download `vault-downloads` from the run page and try the executable in an empty directory.
3. After the candidate and its release version are on `main`, select `main` and run it with **Create a draft release after building the downloads** checked. When GitHub asks, click **Review deployments**, select `release`, and click **Approve and deploy**. This saves a draft with the downloads. Its tag name is the version with a leading `v`, and its target is the commit the workflow built.
4. Open **Releases** and edit the draft. Check the notes, the six executables, the Unix launcher, and `SHA256SUMS`. The workflow marks versions with a suffix as prereleases. For a regular release you want the launcher to download, select **Set as the latest release**. Click **Publish release** to publish the downloads and create the tag. The first regular release marked latest enables the one-line commands in the [setup guide](setup.md). Open the tagged release page to download a prerelease. [How latest download links work](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases)

If the workflow fails, open the failed step in Actions. If an upload stopped partway through, inspect the draft in **Releases**. Delete the incomplete draft before rerunning the workflow for the same version.

Builds cover Intel/AMD 64-bit and ARM64 machines. The binaries are unsigned. To build the same downloads locally on Linux with Go and sha256sum, run `sh installer/build-release.sh /tmp/vault-downloads` from the repository root.
