# Rate Limiting and Secure Logging

Rate limiting protects against brute-force attacks, credential stuffing,
and denial-of-service via resource exhaustion. Apply limits per IP, per
account, and per API key where applicable, with exponential backoff for
repeated failures on sensitive endpoints like login.

Secure logging practices:
- Never log secrets: passwords, API keys, session tokens, or full
  credit card numbers should never appear in logs.
- Log security-relevant events: failed logins, permission denials,
  input validation failures, and administrative actions.
- Return generic error messages to users while logging full details
  (stack traces, internal state) only server-side, so attackers can't
  use verbose errors for reconnaissance.
- Protect log integrity: logs should be append-only or shipped to a
  separate system quickly, so an attacker who compromises the app can't
  easily erase evidence of their activity.
