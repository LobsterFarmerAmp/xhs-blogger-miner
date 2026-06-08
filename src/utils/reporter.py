from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from src.miner.crawler import CrawlResult


@dataclass(slots=True)
class ReportSummary:
    total_bloggers: int
    total_posts_found: int
    total_posts_new: int
    errors: list[str]
    elapsed_seconds: float
    markdown_path: Path


class Reporter:
    def __init__(self, output_dir: str | Path = "data", logger: logging.Logger | None = None) -> None:
        self.output_dir = Path(output_dir)
        self.logger = logger or logging.getLogger("xhs_miner.reporter")

    def generate(self, results: Iterable[CrawlResult], elapsed_seconds: float) -> ReportSummary:
        result_list = list(results)
        errors = [
            f"{result.blogger_user_id}: {result.error_message}"
            for result in result_list
            if result.status != "success"
        ]
        summary = ReportSummary(
            total_bloggers=len(result_list),
            total_posts_found=sum(int(result.posts_found) for result in result_list),
            total_posts_new=sum(int(result.posts_new) for result in result_list),
            errors=errors,
            elapsed_seconds=elapsed_seconds,
            markdown_path=self._write_markdown(result_list, errors, elapsed_seconds),
        )
        self.logger.info(
            "Collection complete: bloggers=%s posts_found=%s posts_new=%s errors=%s elapsed=%.2fs report=%s",
            summary.total_bloggers,
            summary.total_posts_found,
            summary.total_posts_new,
            len(summary.errors),
            summary.elapsed_seconds,
            summary.markdown_path,
        )
        return summary

    def _write_markdown(
        self,
        results: list[CrawlResult],
        errors: list[str],
        elapsed_seconds: float,
    ) -> Path:
        report_dir = self.output_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        path = report_dir / f"xhs_miner_report_{timestamp}.md"
        lines = [
            "# XHS Blogger Miner Report",
            "",
            f"- Generated at: {datetime.now(UTC).isoformat()}",
            f"- Total bloggers crawled: {len(results)}",
            f"- Total posts found: {sum(int(result.posts_found) for result in results)}",
            f"- Total posts new: {sum(int(result.posts_new) for result in results)}",
            f"- Errors encountered: {len(errors)}",
            f"- Time elapsed: {elapsed_seconds:.2f}s",
            "",
            "## Blogger Results",
            "",
        ]
        for result in results:
            lines.append(
                "- "
                f"{result.blogger_user_id}: "
                f"status={result.status}, "
                f"posts_found={result.posts_found}, "
                f"posts_new={result.posts_new}"
            )
        if errors:
            lines.extend(["", "## Errors", ""])
            lines.extend(f"- {error}" for error in errors)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def export_csv(
        self,
        results: list[CrawlResult],
        output_path: Path | None = None,
    ) -> Path:
        if output_path is None:
            report_dir = self.output_dir / "exports"
            report_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            output_path = report_dir / f"xhs_miner_export_{timestamp}.csv"
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["博主ID", "发现帖子", "新增帖子", "状态", "错误信息"])
            for result in results:
                writer.writerow(
                    [
                        result.blogger_user_id,
                        result.posts_found,
                        result.posts_new,
                        result.status,
                        result.error_message,
                    ]
                )
        self.logger.info("CSV export written to %s", output_path)
        return output_path

    def export_json(
        self,
        results: list[CrawlResult],
        output_path: Path | None = None,
    ) -> Path:
        if output_path is None:
            report_dir = self.output_dir / "exports"
            report_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            output_path = report_dir / f"xhs_miner_export_{timestamp}.json"
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)

        data = [
            {
                "blogger_user_id": result.blogger_user_id,
                "posts_found": result.posts_found,
                "posts_new": result.posts_new,
                "status": result.status,
                "error_message": result.error_message,
            }
            for result in results
        ]
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.logger.info("JSON export written to %s", output_path)
        return output_path
