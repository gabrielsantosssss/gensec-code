# SQL Injection

SQL injection occurs when untrusted input is concatenated directly into a
SQL query string, allowing an attacker to alter the query's structure or
logic.

The primary defense is parameterized queries (prepared statements), where
user input is passed as a bound parameter rather than interpolated into
the query text. This applies regardless of the language or ORM in use.

Additional layers of defense include:
- Allow-list input validation (restrict input to expected formats)
- Least-privilege database accounts (the app's DB user should only have
  the permissions it actually needs)
- Escaping output when building dynamic identifiers that can't be
  parameterized (table/column names), using the database driver's own
  escaping functions
- Web application firewalls as a defense-in-depth measure, not a
  substitute for parameterized queries

Stored procedures can help but are not inherently safe if they build
queries internally via string concatenation.
