# Security Policy

## Reporting a vulnerability

Please do not report security vulnerabilities in a public issue or pull request.
Use [GitHub's private vulnerability reporting form](https://github.com/justindobbs/reflex-code-search/security/advisories/new).
If the form is unavailable, open a public issue asking for a private contact
channel. Do not include vulnerability details in that issue.

Include the affected version or commit, the impact, and steps to reproduce the
issue. Please avoid including real credentials or other sensitive data in a
report. The maintainer will follow up privately; there is no guaranteed response
time.

## Supported versions

Security fixes target the latest release. Older releases may not receive fixes;
upgrade to the latest release before reporting an issue when possible.

## Python package installation

The runtime dependency list requires `certifi>=2026.10.19` because HTTPX uses
certifi's CA bundle for HTTPS by default. The October 2026 emSign incident also
affects older pip releases: pip versions before 26.2.2 still trust the
compromised certificates when connecting to package indexes. Upgrade pip in
existing environments using the secure bootstrap instructions in the
[Python packaging incident notice](https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576).
Rebuild container images without cached layers so updated system certificates
are included.

## Handling code and credentials

Local search runs on your machine and does not send repository contents to a
service. If you enable live Jev scoring or smart fallback, the tool sends the
query, candidate file path, and up to the first 2,000 characters of that file's
content to the Jev Decisions API through OpenRouter. The tool applies a
line-based heuristic to redact lines containing common secret-related words,
but this is not a guarantee that secrets will be detected. Do not enable live
scoring for sensitive repositories unless you are comfortable sending that data
to the service.

Keep `OPENROUTER_API_KEY` in an environment variable or another secret store.
Do not commit API keys, credentials, private keys, or sensitive repository data.
