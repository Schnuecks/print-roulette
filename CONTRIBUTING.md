# Contributing to Print Roulette

Thanks for your interest! Bug reports, ideas and pull requests are welcome.

## Reporting problems

Use the issue forms: **Bug report** or **Feature request**. For bugs, please add the
container log. German is fine too.

Security problems go to **Security → Report a vulnerability** instead, see
[SECURITY.md](SECURITY.md).

## Pull requests

1. Open an issue first for larger changes, so we can agree on the approach.
2. Run it locally and make sure the checks pass. The app needs only Python 3.12, no
   packages:

   ```bash
   python app.py            # then open http://localhost:8080
   pip install ruff
   ruff check . && ruff format --check .
   ```

   Without credentials only MakerWorld and Printables are active; set `CULTS_USER`,
   `CULTS_API_KEY` and `THINGIVERSE_TOKEN` to test the others.
3. Keep it small and friendly to the platforms: no extra dependencies, no tracking, no
   storage on the server, and no more requests to the platforms than necessary.
4. Nothing from third parties in the page: scripts, styles and fonts are served locally,
   and the Content Security Policy stays free of inline code.
5. Update README.md and README.de.md if needed and add a line under "Unveröffentlicht" in
   `CHANGELOG.md` if users will notice the change.

The pull request template has a short checklist for this.

## Code layout

| Path | Contents |
|---|---|
| `app.py` | Web server, the four platform sources, filters, rate limit and security headers |
| `static/index.html` | Page skeleton |
| `static/app.js` | Wheel, rolling, filters, history and keyboard |
| `static/style.css` | Design, light and dark mode |
| `static/fonts/` | Playfair Display and Manrope (SIL Open Font License) |
| `static/logo.svg`, `og.png`, `apple-touch-icon.png` | Logo, link preview and app icon |

## License

By contributing you agree that your contribution is released under the
[GNU Affero General Public License, version 3 or later](LICENSE).
