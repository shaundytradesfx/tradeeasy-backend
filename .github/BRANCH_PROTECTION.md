# Branch Protection Rules for TradeEasy Backend

This file documents the recommended branch protection rules for the TradeEasy Backend repository.

## Main Branch Protection

Configure these settings on GitHub after creating the repository:

1. Go to the repository on GitHub
2. Navigate to Settings → Branches → Branch protection rules
3. Click "Add rule"
4. In "Branch name pattern" enter: `main`
5. Enable the following settings:
   - ✅ Require a pull request before merging
   - ✅ Require approvals (set to 1 or more)
   - ✅ Dismiss stale pull request approvals when new commits are pushed
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators
   - ✅ Require linear history
   
6. Click "Create" or "Save changes"

## Development Branch

It's recommended to create a `develop` branch for ongoing development:

```bash
git checkout -b develop
git push -u origin develop
```

You may want to add similar but less strict protection rules for the develop branch. 