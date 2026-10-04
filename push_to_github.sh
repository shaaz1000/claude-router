#!/usr/bin/env bash
# Publish this repo to GitHub. Run from the repo folder: bash push_to_github.sh
# Uses the GitHub CLI if installed (https://cli.github.com), else asks for your username.
set -e
NAME="${1:-claude-router}"
if command -v gh >/dev/null 2>&1; then
  gh auth status >/dev/null 2>&1 || gh auth login
  gh repo create "$NAME" --public --source . --remote origin --push \
    --description "Automatic model and effort routing for Claude Code: Haiku, Sonnet, Opus per prompt, zero token classification"
  gh repo edit --add-topic claude-code --add-topic anthropic --add-topic llm-routing --add-topic ai-engineering
  echo "Done: $(gh repo view --json url -q .url)"
else
  read -rp "GitHub username: " U
  echo "1. Create an empty repo named $NAME at https://github.com/new (no README)."
  read -rp "2. Press Enter when created... "
  git remote remove origin 2>/dev/null || true
  git remote add origin "https://github.com/$U/$NAME.git"
  git push -u origin main
  sed -i.bak "s#<your-username>#$U#" README.md && rm -f README.md.bak
  git commit -am "docs: set clone URL" && git push
fi
