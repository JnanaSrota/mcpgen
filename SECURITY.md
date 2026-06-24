# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report security issues by emailing the maintainer directly via the contact on their [GitHub profile](https://github.com/JnanaSrota). Include:

- A description of the vulnerability
- Steps to reproduce it
- The potential impact

You will receive a response within 48 hours. If the issue is confirmed, a patch will be released as quickly as possible.

## Scope

mcpgen is a code generation tool — it reads API specs and writes Python files to disk. Security considerations include:

- **Spec fetching** — mcpgen fetches remote URLs you provide. Only point it at specs you trust.
- **Generated code** — review generated `server.py` files before running them, especially the auth/token handling sections.
- **No runtime dependency** — mcpgen is not required at runtime, reducing the attack surface of your deployed server.
