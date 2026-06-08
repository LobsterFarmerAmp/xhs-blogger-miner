from __future__ import annotations

import argparse
import asyncio

from src.config_loader import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xhs-miner")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--all", action="store_true", help="Crawl all configured bloggers")
    target.add_argument("--blogger", help="Crawl a specific blogger user_id")
    parser.add_argument("--config", help="Path to bloggers YAML config")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without crawling")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        default=None,
        help="Run Chrome headless",
    )
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Run Chrome with a visible window",
    )
    return parser


async def run(args: argparse.Namespace) -> None:
    from src.mediacrawler import ensure_mediacrawler_path

    ensure_mediacrawler_path()

    from src.pipeline import Pipeline

    settings = load_settings()
    if args.verbose:
        settings.LOG_LEVEL = "DEBUG"
    if args.headless is not None:
        settings.HEADLESS = args.headless

    pipeline = Pipeline(settings, bloggers_config_path=args.config)
    if args.dry_run:
        await pipeline.run_dry_run()
    elif args.blogger:
        await pipeline.run_one(args.blogger)
    else:
        await pipeline.run_all()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.all and not args.blogger and not args.dry_run:
        parser.error("Specify --all, --blogger <id>, or --dry-run")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
