# xhs-blogger-miner

Config-driven Xiaohongshu (XHS) blogger data collection tool that stores blogger profiles, posts, crawl logs, and crawl summaries locally.

## Features

- Crawl all configured bloggers or a single blogger from the command line.
- Accept creator homepage URLs or 24-character XHS user IDs.
- Collect blogger profile data, note metadata, media URLs, tags, and interaction counts.
- Persist results to SQLite and write logs/reports under the configured data directory.
- Reuse MediaCrawler for XHS browser, signing, cookie, and API behavior.
- Apply human-like delays and rate-limit-aware retries.

## Prerequisites

- Python 3.11 or newer.
- `uv` for dependency management and command execution.
- Playwright browser dependencies installed locally.
- MediaCrawler available at `MEDIACRAWLER_PATH`, or at the default `~/.openclaw/tools/MediaCrawler`.
- Valid XHS login state, either through `COOKIES` or an interactive QR-code login flow.

## Quick Start

1. Install dependencies:

   ```bash
   uv sync
   uv run playwright install chromium
   ```

2. Configure environment variables:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` as needed. Set `MEDIACRAWLER_PATH` if MediaCrawler is not installed at `~/.openclaw/tools/MediaCrawler`.

3. Configure target bloggers in `config/bloggers.yaml`:

   ```yaml
   bloggers:
     - user_id: "5986da286a6a692eaf2a53a1"
       nickname: "example"
       homepage_url: "https://www.xiaohongshu.com/user/profile/5986da286a6a692eaf2a53a1"
       notes:
         max_count: 50
   ```

4. Validate configuration without crawling:

   ```bash
   uv run xhs-miner --dry-run
   ```

5. Run a crawl:

   ```bash
   uv run xhs-miner --all
   uv run xhs-miner --blogger 5986da286a6a692eaf2a53a1
   ```

## Configuration Reference

Environment settings are loaded from `.env` by `config/settings.py`.

| Name | Default | Description |
| --- | --- | --- |
| `MEDIACRAWLER_PATH` | `~/.openclaw/tools/MediaCrawler` | Local MediaCrawler checkout path. |
| `CRAWLER_MAX_POSTS_PER_BLOGGER` | `50` | Default maximum notes to collect per blogger. |
| `CRAWLER_MIN_SLEEP_SEC` | `3` | Minimum delay between crawler actions. |
| `CRAWLER_MAX_SLEEP_SEC` | `10` | Maximum delay and retry backoff cap. |
| `SAVE_DATA_PATH` | `data` | Directory for logs and reports. |
| `DATABASE_PATH` | `data/xhs_bloggers.db` | SQLite database path. |
| `LOG_LEVEL` | `INFO` | Python logging level. |
| `HEADLESS` | `true` | Run Chromium headless when true. |
| `COOKIES` | empty | XHS cookie string. Empty values trigger login flow. |
| `XHS_CRAWLER_TYPE` | `creator` | MediaCrawler XHS crawler mode. |
| `CDP_DEBUG_PORT` | `9222` | Chrome DevTools Protocol port. |
| `CDP_CONNECT_EXISTING` | `false` | Connect to an existing browser when true. |

`config/bloggers.yaml` must contain a non-empty `bloggers` list. Each blogger needs either `homepage_url` or `user_id`; `notes.max_count` overrides the default per-blogger note limit.

## Project Structure

```text
config/                 Runtime settings and blogger targets
src/config_loader.py    Settings and YAML loading
src/main.py             CLI entry point
src/pipeline.py         Crawl orchestration
src/mediacrawler.py     MediaCrawler import path setup
src/miner/              Browser, login, human simulation, and crawler logic
src/extractor/          Blogger and post normalization
src/storage/            SQLite models and database access
src/utils/              Logging and reporting helpers
tests/                  Unit tests
```

## Rate Limiting and Anti-Detection Notes

XHS can throttle or block requests when access patterns look automated. Keep `CRAWLER_MIN_SLEEP_SEC` and `CRAWLER_MAX_SLEEP_SEC` conservative, avoid large `notes.max_count` values, and prefer authenticated sessions. The crawler treats messages containing `429`, `rate limit`, `too many requests`, or the Chinese frequent-access wording as rate limits and backs off exponentially with jitter before retrying.

Use this project responsibly and follow XHS terms, robots guidance, and applicable laws. Do not use it for high-volume scraping or disruptive access patterns.
