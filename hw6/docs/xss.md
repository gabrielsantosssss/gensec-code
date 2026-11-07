# Cross-Site Scripting (XSS)

XSS occurs when an application includes untrusted data in a web page
without proper validation or escaping, allowing an attacker to run
arbitrary script in a victim's browser.

Three common types:
- Reflected XSS: malicious input is reflected back in an immediate
  response (e.g. a search results page)
- Stored XSS: malicious input is saved server-side (e.g. a comment) and
  served to other users later
- DOM-based XSS: the vulnerability exists in client-side JavaScript that
  writes untrusted data into the DOM

Primary defenses:
- Contextual output encoding: encode data differently depending on where
  it's inserted (HTML body, HTML attribute, JavaScript, URL, CSS)
- Use templating engines that auto-escape by default (e.g. Jinja2) rather
  than building HTML via string concatenation
- Content-Security-Policy headers to restrict script sources as a
  defense-in-depth layer
- Validate and sanitize input, but never rely on input validation alone
  as the only XSS defense — output encoding is what actually matters
