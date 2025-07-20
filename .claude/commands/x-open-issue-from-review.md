---
allowed-tools: Bash(gh pr:*), Bash(gh issue create:*), Bash(gh api:*)
description: Open the issue from PR review
---

# Your Task
Please open the issue according to PR review: $ARGUMENTS.

# Follow these steps:
1. Use 'gh pr view $ARGUMENTS' to get the PR detail
2. Understand the problem described in the review comment.
3. Search the codebase for relevant files.
4. Open the issues if you determine that any revisions are necessary based on the review comment. Use 'gh issue create'.

# Context
- Remember to use the GitHub CLI ('gh') for all Github-related tasks.
- Opening issues, you have to follow the rules of format described CLAUDE.md or in the files under the .claude directory.
- For anything not covered here, follow the rules specified in CLAUDE.md and in the files under the .claude directory.
