# Building with GitHub Copilot and recording it with Entire

Two partner categories are worth entering for this project because they match how you will actually work:

- **Best Use of GitHub Copilot:** build with Copilot's coding agent, the Copilot CLI or the Copilot app, automate the project with GitHub Actions, or review contributors' pull requests with Copilot.
- **Best Use of Entire:** share the agent sessions behind your project in the write-up.

Only enter a category if you genuinely used it. The judges look at whether the use is meaningful, and the post must describe what you really did.

## Order matters: enable Entire before the agent work

Entire records sessions from the moment it is enabled, so set it up first.

1. Create the GitHub repository and push this folder.
2. Install the Entire CLI (needs Git 2.25 or newer; hooks need Bash or Zsh):
   - macOS: `brew tap entireio/tap`, then `brew trust entireio/tap`, then `brew install --cask entire`
   - Linux: `curl -fsSL https://entire.io/install.sh | bash`
   - Windows: `scoop bucket add entire https://github.com/entireio/scoop-bucket.git` then `scoop install entire/cli`
   - Any system with Go 1.21+: `go install github.com/entireio/cli/cmd/entire@latest`
   - Check it worked with `entire version`. The `entire` binary must be on your PATH.
3. In the repository, run `entire enable -y --agent copilot-cli`. This installs Git hooks and the hook configuration for Copilot CLI.
4. Commit the `.entire/settings.json` and `.entire/.gitignore` files it creates.
5. The commands change over time, so check https://docs.entire.io/quickstart if anything fails.

## Installing Copilot CLI

- Needs an active GitHub Copilot subscription. If Copilot comes through an organisation, an administrator may have disabled the CLI.
- Install with `npm install -g @github/copilot` (macOS, Linux, Windows), or `winget install GitHub.Copilot` (Windows), or `brew install copilot-cli` (macOS, Linux).
- Run `copilot` inside the repository and follow the prompts to sign in and trust the folder.
- Each prompt counts against your monthly premium-request quota, so write prompts that ask for a whole task.

## How the work gets captured

- Work with Copilot CLI inside the repository.
- Entire creates a checkpoint when you commit. Commit after each small task so each checkpoint maps to one piece of work.
- Checkpoint data lives on a separate Git branch named `entire/checkpoints/v1`. A normal `git push` also syncs it.
- Browse the captured sessions on entire.io, and link to them from your post.

## What to build with Copilot

`docs/COPILOT_TASKS.md` lists real improvements with acceptance criteria. Each one is small enough to finish in an hour or two. Use Copilot CLI (or assign an issue to the Copilot coding agent if your plan includes it) and review what it produces before committing. `.github/copilot-instructions.md` already tells Copilot the rules of this repository.

For each task, record in `docs/BUILD_LOG.md`: the date, the tool, what you asked for, and the commit or pull request. Include the cases where Copilot got something wrong and you fixed it; that is the interesting part of the write-up.

## GitHub Actions

`.github/workflows/ci.yml` runs the test suite on every push and pull request. Once the repository is on GitHub, check that the first run is green, and mention it in the post if you like.

## Be accurate about the scaffold

The initial scaffold in this repository was generated with Claude, outside Entire and Copilot. It is in the first commit and has no Entire session. Say so plainly in the post and in the build log. Everything after that first commit is what you can truthfully attribute to Copilot and capture with Entire.
