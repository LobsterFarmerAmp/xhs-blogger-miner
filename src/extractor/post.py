from __future__ import annotations

import json
from typing import Any

from src.mediacrawler import ensure_mediacrawler_path
from src.storage.models import Post

ensure_mediacrawler_path()

try:
    from tools.crawler_util import normalize_interaction_count
except ImportError:
    def normalize_interaction_count(count_str: str | None) -> dict[str, int | str]:
        if count_str is None:
            return {"raw": "", "value": 0}
        raw = str(count_str).strip()
        if not raw:
            return {"raw": raw, "value": 0}
        try:
            lower = raw.lower()
            if lower.endswith("w"):
                value = round(float(raw[:-1]) * 10000)
            elif lower.endswith("万"):
                value = round(float(raw[:-1]) * 10000)
            elif lower.endswith("k"):
                value = round(float(raw[:-1]) * 1000)
            elif lower.endswith("m"):
                value = round(float(raw[:-1]) * 1000000)
            else:
                value = int(float(raw))
            return {"raw": raw, "value": value}
        except (ValueError, TypeError):
            return {"raw": raw, "value": 0}


class PostExtractor:
    def extract_post_data(
        self,
        note_card: dict[str, Any],
        blogger_user_id: str | None = None,
        listing_data: str = "",
    ) -> Post:
        user_info = note_card.get("user") or {}
        interact_info = note_card.get("interact_info") or {}
        note_id = str(note_card.get("note_id") or note_card.get("id") or "")
        user_id = blogger_user_id or user_info.get("user_id") or note_card.get("user_id") or ""

        liked = self.normalize_count(
            note_card.get("liked_count", interact_info.get("liked_count"))
        )
        collected = self.normalize_count(
            note_card.get("collected_count", interact_info.get("collected_count"))
        )
        comment = self.normalize_count(
            note_card.get("comment_count", interact_info.get("comment_count"))
        )
        share = self.normalize_count(
            note_card.get("share_count", interact_info.get("share_count"))
        )

        return Post(
            note_id=note_id,
            blogger_user_id=str(user_id),
            type=str(note_card.get("type") or ""),
            title=str(note_card.get("title") or note_card.get("display_title") or ""),
            description=str(note_card.get("desc") or note_card.get("description") or ""),
            publish_time=int(note_card.get("time") or note_card.get("publish_time") or 0),
            last_update_time=int(note_card.get("last_update_time") or 0),
            note_url=self._note_url(note_id, note_card),
            liked_count_raw=str(liked["raw"]),
            liked_count_value=int(liked["value"]),
            collected_count_raw=str(collected["raw"]),
            collected_count_value=int(collected["value"]),
            comment_count_raw=str(comment["raw"]),
            comment_count_value=int(comment["value"]),
            share_count_raw=str(share["raw"]),
            share_count_value=int(share["value"]),
            image_urls=self._extract_image_urls(note_card),
            video_url=self._extract_video_url(note_card),
            tag_list=self._extract_tags(note_card),
            ip_location=str(note_card.get("ip_location") or ""),
            xsec_token=str(note_card.get("xsec_token") or ""),
            listing_data=listing_data or note_card.get("listing_data", ""),
        )

    def extract_listing_post(
        self, note_card: dict[str, Any], blogger_user_id: str
    ) -> dict[str, Any]:
        """Create a skeletal post record from listing API data.

        Used as fallback when detail fetch fails — preserves listing-level
        fields (title, publish_time, xsec_token, etc.) so the post is at
        least partially available. Fields that require detail API
        (full description, interact counts, tags, media) are left empty.
        """
        note_id = str(note_card.get("note_id") or note_card.get("id") or "")
        publish_time = self._decode_note_id_timestamp(note_id)
        title = str(note_card.get("display_title") or note_card.get("title") or "")
        return {
            "note_id": note_id,
            "blogger_user_id": blogger_user_id,
            "type": str(note_card.get("type") or ""),
            "title": title,
            "publish_time": publish_time,
            "last_update_time": int(note_card.get("last_update_time") or 0),
            "note_url": self._note_url(note_id, note_card),
            "xsec_token": str(note_card.get("xsec_token") or ""),
            "listing_data": json.dumps(note_card, ensure_ascii=False),
        }

    @staticmethod
    def decode_note_id_timestamp(note_id: str) -> int:
        """Decode publish_time from note_id first 8 hex chars.

        XHS note_id format: first 8 chars = hex-encoded Unix timestamp (seconds).
        Example: 6a27fa08 -> int(0x6a27fa08) = 1781029384.

        Returns 0 if note_id is too short or not valid hex.
        """
        if len(note_id) >= 8:
            try:
                return int(note_id[:8], 16)
            except (ValueError, TypeError):
                pass
        return 0

    def _decode_note_id_timestamp(self, note_id: str) -> int:
        return self.decode_note_id_timestamp(note_id)

    @staticmethod
    def normalize_count(count: Any) -> dict[str, int | str]:
        if isinstance(count, dict) and "raw" in count and "value" in count:
            return {"raw": str(count["raw"]), "value": int(count["value"] or 0)}
        return normalize_interaction_count(count)

    def _note_url(self, note_id: str, note_card: dict[str, Any]) -> str:
        if note_card.get("note_url"):
            return str(note_card["note_url"])
        xsec_token = note_card.get("xsec_token")
        if xsec_token:
            return (
                "https://www.xiaohongshu.com/explore/"
                f"{note_id}?xsec_token={xsec_token}&xsec_source=pc_feed"
            )
        return f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else ""

    def _extract_image_urls(self, note_card: dict[str, Any]) -> list[str]:
        image_list = note_card.get("image_urls") or note_card.get("image_list") or []
        if isinstance(image_list, str):
            return self._parse_string_list(image_list)

        urls: list[str] = []
        for image in image_list:
            if isinstance(image, str):
                urls.append(image)
                continue
            if not isinstance(image, dict):
                continue
            for key in ("url_default", "url", "url_pre", "url_size_large"):
                if image.get(key):
                    urls.append(str(image[key]))
                    break
            for info in image.get("info_list") or []:
                if isinstance(info, dict) and info.get("url"):
                    urls.append(str(info["url"]))
        return list(dict.fromkeys(urls))

    def _extract_video_url(self, note_card: dict[str, Any]) -> str:
        if note_card.get("video_url"):
            return str(note_card["video_url"])

        video = note_card.get("video") or {}
        if not isinstance(video, dict):
            return ""

        stream = video.get("media", {}).get("stream", {}) if isinstance(video.get("media"), dict) else {}
        for stream_list in stream.values() if isinstance(stream, dict) else []:
            if not isinstance(stream_list, list):
                continue
            for item in stream_list:
                if isinstance(item, dict) and item.get("master_url"):
                    return str(item["master_url"])
        return str(video.get("url") or "")

    def _extract_tags(self, note_card: dict[str, Any]) -> list[str]:
        tags = note_card.get("tag_list") or []
        if isinstance(tags, str):
            return self._parse_string_list(tags)

        names: list[str] = []
        for tag in tags:
            if isinstance(tag, str):
                names.append(tag)
            elif isinstance(tag, dict) and tag.get("name"):
                names.append(str(tag["name"]))
        return names

    @staticmethod
    def _parse_string_list(raw: str) -> list[str]:
        stripped = raw.strip()
        if not stripped:
            return []
        try:
            loaded = json.loads(stripped)
        except json.JSONDecodeError:
            return [part.strip() for part in stripped.split(",") if part.strip()]
        if isinstance(loaded, list):
            return [str(item) for item in loaded if item]
        return []
