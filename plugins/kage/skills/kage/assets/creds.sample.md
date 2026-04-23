# Target Credentials

Fill this in before hunting. Kage reads this file in Turn 0 for
authentication and scope. Rename to `creds.md` in your engagement folder.

## Target
<!-- example.com -->

## Accounts

### Attacker (Account A)
- Email:
- Password:
- Role: regular user

### Victim (Account B)
- Email:
- Password:
- Role: regular user

### Admin (if available)
- Email:
- Password:
- Role: admin

## Tokens / Cookies

### Session Cookie (after login)
```
<!-- session=abc123; csrf_token=xyz789 -->
```

### API Token
```
<!-- Bearer eyJhbGciOiJIUzI1... -->
```

### OAuth
- Client ID:
- Client Secret:
- Redirect URI:

## AgentMail (optional — disposable inboxes for account creation)

Used by the bundled `agentmail` reference
(`references/agentmail/SKILL.md`) to spin up throwaway inboxes when the
target allows self-service registration. Lets you create N accounts,
receive verification emails, and click through to populate the
`Attacker` / `Victim` token sections above.

- API Key:     <!-- am_... from https://agentmail.com/settings -->
- Base domain: <!-- leave blank for auto-generated @agentmail.to addresses -->

Leave the API key blank to skip — everything else in Kage works without it.

## GitHub (optional — for gitmail.py OSINT in Turn 1)

Used by `scripts/gitmail.py` to enumerate repos, emails, and leaked
secrets against GitHub organizations / users tied to the target. Without
a token, gitmail hits the unauthenticated rate limit (60 req/hr) and
gives up fast. With one, 5,000 req/hr and TruffleHog scans on public
repos become feasible.

- Token: <!-- ghp_... — create at github.com/settings/tokens (public_repo scope is enough) -->
- Guessed org/user: <!-- e.g. for example.com try "example" or "exampleinc" -->

## Scope
- In scope:
- Out of scope:
- Platform: <!-- HackerOne / Bugcrowd / Intigriti / VDP -->
- Program URL:

## Notes
<!-- Any extra context: WAF type, rate limits, special auth flow, etc. -->
