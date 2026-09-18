# Getting this project onto GitHub (beginner guide)

This guide assumes you have never used Git or GitHub. It is split into
**what you do once** (about 20 minutes, mostly waiting for downloads) and
**what Claude does** from inside this project afterwards. Nothing here is
dangerous; every step is reversible.

## The vocabulary you need (and may be asked about)

| Word | Meaning in one sentence |
|---|---|
| **Git** | A program on your Mac that records snapshots of a folder over time. |
| **Repository (repo)** | A folder whose history Git tracks. This project folder is one. |
| **Commit** | One saved snapshot with a message saying what changed and why. |
| **GitHub** | A website that stores a copy of your repo so others can read it. |
| **Push** | Sending your local commits up to GitHub. |
| **Remote** | GitHub's copy of the repo, from your Mac's point of view. |
| **Branch** | A parallel line of commits; `main` is the default one. |
| **Pull request (PR)** | A proposal to merge one branch into another, with a review. |
| **README** | The front page of a repo; the first thing a reviewer reads. |
| **`.gitignore`** | A list of files Git should never record (caches, secrets, databases). |

## Part 1: one-time setup on your Mac (you do this)

Your Mac currently has none of the developer tools installed. Homebrew is
the standard package manager for macOS developers; installing it also
installs Apple's Command Line Tools, which contain Git.

1. Open **Terminal** (press `Cmd + Space`, type `Terminal`, press Return),
   or use the Terminal panel inside the Claude app.
2. Paste this and press Return. It asks for your Mac login password
   (nothing appears while you type it; that is normal) and takes 5–15 minutes.

   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

3. When it finishes it prints two or three lines under **"Next steps"**
   that start with `echo` and `eval`. Copy and run exactly those lines; they
   put `brew` on your PATH. Then close and reopen Terminal.
4. Install Python and the GitHub command-line tool:

   ```bash
   brew install python@3.12 gh
   ```

5. Check everything works. Each command should print a version, not an error:

   ```bash
   git --version && python3.12 --version && gh --version
   ```

## Part 2: your GitHub account (you do this, in a browser)

1. Go to <https://github.com/signup> and create an account. Use an email you
   check. Choose the username carefully: it will be in the link you send the
   club (for example `github.com/baronzhang/dock-scheduler`).
2. Verify the email GitHub sends you.
3. Back in Terminal, log the command-line tool into that account:

   ```bash
   gh auth login
   ```

   Answer the prompts with: **GitHub.com** → **HTTPS** → **Yes** (authenticate
   Git with your GitHub credentials) → **Login with a web browser**. It shows
   an 8-character code; press Return, paste the code into the browser tab that
   opens, and approve. Terminal then says "Logged in as <your username>".

4. Tell Git who you are (this name and email are stamped on every commit;
   they are public if the repo is public). Replace the values if you prefer
   a different name or GitHub's no-reply address:

   ```bash
   git config --global user.name "Baron Zhang"
   ```

   ```bash
   git config --global user.email "baronzhang2007@gmail.com"
   ```

Then come back to the Claude session and say **"setup done"**.

## Part 3: what Claude does next (you watch)

Once Git exists on the machine, Claude will, from inside the project folder:

1. `git init` to start tracking the folder, and add a `.gitignore`.
2. Make the first commit: the framework document, this guide, the README,
   and the sample data.
3. Create the GitHub repo and push in one command:

   ```bash
   gh repo create dock-scheduler --public --source=. --remote=origin --push
   ```

4. Give you the link `https://github.com/<your username>/dock-scheduler`.
   Open it: you should see the README rendered on the front page.

Public is the right choice for a club application: reviewers can open the
link without being invited. Nothing private goes in this repo (the sample
data is synthetic; the `.gitignore` keeps local databases and caches out).

## Part 4: the working rhythm after that

- Claude commits after each meaningful step with a message that explains the
  *why*. Small, well-named commits are themselves something reviewers look at.
- Features are built on short-lived branches and merged through pull requests
  when it helps the story (for example one PR per phase of the framework),
  so the repo shows how the work was structured, not just the end state.
- You can always look at `git log --oneline` to read the history, and at the
  **Commits** and **Pull requests** tabs on GitHub.
- If something ever goes wrong locally, nothing is lost once it is pushed:
  GitHub has the full copy.

## Part 5: what to send the club

Send the repo link. Make sure, before you send it, that:

1. The README explains what the project does, how to run it, the assumptions,
   and the decisions (the framework document is linked from it).
2. `git log` reads like a story of the six hours.
3. The live demo link (GitHub Pages) works in a private browser window.

## If you get stuck

- `command not found: brew` after installing: you skipped step 3 of Part 1
  (the `echo`/`eval` lines). Rerun the installer; it prints them again.
- `gh auth login` cannot open a browser: choose "Paste an authentication
  token" instead and follow GitHub's instructions on the screen.
- Anything else: paste the exact error text into the Claude session.
