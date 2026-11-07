# OAuth 2.0 Security Considerations

OAuth 2.0 is an authorization framework, not an authentication protocol by
itself — authentication on top of OAuth is typically handled by OpenID
Connect (OIDC).

Key security practices:
- Always use the Authorization Code flow with PKCE (Proof Key for Code
  Exchange), even for confidential clients, since PKCE mitigates
  authorization code interception attacks.
- Avoid the Implicit flow; it exposes access tokens in the URL fragment
  and has largely been deprecated in favor of Authorization Code + PKCE.
- Validate the `state` parameter to prevent CSRF attacks against the
  OAuth redirect flow.
- Use short-lived access tokens with refresh tokens rather than
  long-lived access tokens.
- Register exact redirect URIs (no wildcards) to prevent open-redirect
  style token theft.
- Store tokens securely: never in localStorage for browser apps (XSS can
  read them); prefer httpOnly, secure, SameSite cookies or in-memory
  storage for SPAs.
