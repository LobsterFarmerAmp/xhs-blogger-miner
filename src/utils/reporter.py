from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


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

    def generate(self, results: Iterable[object], elapsed_seconds: float) -> ReportSummary:
        result_list = list(results)
        errors = [
            f"{result.blogger_user_id}: {result.error_message}"
            for result in result_list
            if getattr(result, "status", "") != "success"
        ]
        summary = ReportSummary(
            total_bloggers=len(result_list),
            total_posts_found=sum(int(getattr(result, "posts_found", 0)) for result in result_list),
            total_posts_new=sum(int(getattr(result, "posts_new", 0)) for result in result_list),
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
        results: list[object],
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
            f"- Total posts found: {sum(int(getattr(result, 'posts_found', 0)) for result in results)}",
            f"- Total posts new: {sum(int(getattr(result, 'posts_new', 0)) for result in results)}",
            f"- Errors encountered: {len(errors)}",
            f"- Time elapsed: {elapsed_seconds:.2f}s",
            "",
            "## Blogger Results",
            "",
        ]
        for result in results:
            lines.append(
                "- "
                f"{getattr(result, 'blogger_user_id', '')}: "
                f"status={getattr(result, 'status', '')}, "
                f"posts_found={getattr(result, 'posts_found', 0)}, "
                f"posts_new={getattr(result, 'posts_new', 0)}"
            )
        if errors:
            lines.extend(["", "## Errors", ""])
            lines.extend(f"- {error}" for error in errors)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
