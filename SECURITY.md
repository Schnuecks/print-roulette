# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems. Report them privately through
GitHub instead: on the repository page open **Security → Report a vulnerability**. You will
get an answer within a few days, and a fix is released as soon as possible.

If that option is not shown, contact the maintainer [@Schnuecks](https://github.com/Schnuecks)
through GitHub and ask for a private channel, without describing the problem publicly.

Helpful details: the Print Roulette version (first log line or `python app.py --version`),
how it is deployed (behind a reverse proxy or directly) and the steps to reproduce.

## Supported versions

Security fixes go into the latest release. Please update to it before reporting.

## Scope

Print Roulette is a small web server without accounts or a database. It fetches random
models from the platforms and passes title, link and preview image on to the browser.

- Only HTTPS links and images on known hosts of the four platforms reach the browser;
  everything else is dropped.
- The page uses a strict Content Security Policy without inline code and loads no scripts,
  styles or fonts from third parties.
- Credentials for Cults3D and Thingiverse are read from the environment or, preferably,
  from files (`*_FILE`, e.g. Docker secrets). They are never logged or sent to the browser.
- Requests are rate-limited per IP (`RATE_PER_MINUTE`) and at most `MAX_ROLLS` rolls run at
  the same time. Requests to the platforms time out after a few seconds, and Cults3D is
  refilled by one request at a time with a pause after errors.
- `X-Forwarded-*` headers are ignored unless `TRUST_PROXY=1`. Behind a proxy the client
  address is taken `TRUSTED_PROXY_HOPS` entries from the end of `X-Forwarded-For`, so values a
  client puts in front do not count. Only enable it behind a proxy that sets the header.
- Base image and GitHub Actions are pinned to digests and commit SHAs; Dependabot updates them.
- The container runs as an unprivileged user and works with a read-only file system and
  without capabilities.
