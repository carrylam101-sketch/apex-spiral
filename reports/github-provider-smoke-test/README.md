# GitHub Provider Smoke Test

This file verifies that Hermes can write to `carrylam101-sketch/apex-spiral` with the configured GitHub token.

Evidence gates:
- API `/user` works
- API `/rate_limit` works
- Repo read/write permission exists for `carrylam101-sketch/apex-spiral`
- Git fetch works via token-backed credentials
- Token is stored only in `~/.hermes/.env` and is not included in this repository
