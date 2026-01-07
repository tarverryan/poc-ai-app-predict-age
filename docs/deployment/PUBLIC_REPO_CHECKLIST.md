# Public Repository Safety Checklist

This checklist helps ensure the repository is safe for public release with no sensitive information, credentials, or proprietary data.

## Secret Scan Patterns

Search the repository for these patterns (case-insensitive):

- **AWS Access Keys:** `AKIA[0-9A-Z]{16}`
- **AWS Secret Keys:** Pattern matching `[A-Za-z0-9/+=]{40}`
- **Private Keys:** `BEGIN PRIVATE KEY`, `BEGIN RSA PRIVATE KEY`, `BEGIN EC PRIVATE KEY`
- **API Keys:** `sk-`, `xox`, `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`
- **Database Credentials:** `password=`, `pwd=`, `passwd=`
- **JWT Secrets:** `JWT_SECRET`, `SECRET_KEY`
- **OAuth Tokens:** `oauth_token`, `access_token`

**Command to scan:**
```bash
# Search for common secret patterns
grep -r -i "AKIA\|BEGIN PRIVATE KEY\|sk-\|xox\|password=" --exclude-dir=.git --exclude-dir=node_modules .
```

## Data and PII Check

- [ ] No real personal identifiable information (PII) in code or data
- [ ] No real email addresses, phone numbers, or addresses
- [ ] Sample data is synthetic or anonymized
- [ ] No proprietary datasets or business data
- [ ] Database names are generic (not organization-specific)
- [ ] Table names are generic (not customer/proprietary names)

## Credentials and Configuration

- [ ] No hardcoded AWS account IDs
- [ ] No hardcoded S3 bucket names (use variables/placeholders)
- [ ] No hardcoded API keys or secrets
- [ ] All credentials use environment variables
- [ ] `.env` files are in `.gitignore`
- [ ] `.env.example` exists with placeholder values
- [ ] Terraform variables use placeholders, not real values
- [ ] No real AWS resource ARNs in code

## Links and Access

- [ ] All GitHub links point to public repositories
- [ ] No links to private/internal systems
- [ ] No links requiring authentication
- [ ] Documentation links are publicly accessible
- [ ] No references to internal tools or systems

## Code and Comments

- [ ] No organization-specific naming in code
- [ ] No references to employer or customers
- [ ] Comments don't reveal proprietary information
- [ ] No TODO comments with sensitive information
- [ ] No debug code with real data

## Files to Verify

- [ ] `.gitignore` properly configured
- [ ] No `.env`, `.aws/`, or credential files committed
- [ ] No `*.tfstate` or `*.tfstate.backup` files
- [ ] No deployment ZIP files with secrets
- [ ] No log files with sensitive data
- [ ] No test result files with real data

## Documentation

- [ ] No production/business metrics in README
- [ ] No specific cost numbers from real deployments
- [ ] No customer or business impact statements
- [ ] Documentation focuses on learning, not production use
- [ ] Author information is clear and accurate

## Quick Verification Commands

```bash
# Check for AWS account IDs (replace with your pattern)
grep -r "864923771507\|your-account-id-pattern" --exclude-dir=.git .

# Check for hardcoded bucket names (should use variables)
grep -r "s3://[a-z0-9-]\+" --exclude-dir=.git . | grep -v "var\|\\$"

# Check for private keys
grep -r "BEGIN.*PRIVATE KEY" --exclude-dir=.git .

# Check git history for secrets (if rewriting history)
git log --all --source --grep="secret\|password\|key" -i
```

## Pre-Commit Checklist

Before pushing to public repository:

1. Run secret scan patterns above
2. Review all environment variable usage
3. Verify `.gitignore` excludes sensitive files
4. Check for any organization-specific references
5. Review README and documentation for production language
6. Verify all links are publicly accessible

## If Secrets Are Found

1. **DO NOT** commit the fix directly
2. Rotate/revoke the exposed secret immediately
3. Remove secret from code and git history
4. Use `git filter-branch` or BFG Repo-Cleaner to remove from history
5. Force push to update remote repository

---

**Last Updated:** January 2025  
**Author:** Ryan Tarver

