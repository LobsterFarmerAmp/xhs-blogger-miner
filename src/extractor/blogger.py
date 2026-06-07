from __future__ import annotations

from typing import Any

from src.extractor.post import PostExtractor
from src.storage.models import Blogger


class BloggerExtractor:
    def extract_blogger_data(
        self,
        creator_info: dict[str, Any],
        user_id: str = "",
        homepage_url: str = "",
        nickname: str = "",
    ) -> Blogger:
        basic_info = creator_info.get("basicInfo") or creator_info.get("basic_info") or {}
        interactions = creator_info.get("interactions") or []
        interaction_counts = self._interaction_counts(interactions)

        return Blogger(
            user_id=str(
                user_id
                or basic_info.get("userId")
                or basic_info.get("user_id")
                or creator_info.get("user_id")
                or ""
            ),
            nickname=str(nickname or basic_info.get("nickname") or creator_info.get("nickname") or ""),
            avatar=str(basic_info.get("images") or basic_info.get("avatar") or creator_info.get("avatar") or ""),
            description=str(basic_info.get("desc") or basic_info.get("description") or ""),
            gender=self._gender(basic_info.get("gender")),
            ip_location=str(basic_info.get("ipLocation") or basic_info.get("ip_location") or ""),
            followers_count=interaction_counts["followers_count"],
            following_count=interaction_counts["following_count"],
            total_likes=interaction_counts["total_likes"],
            homepage_url=homepage_url,
        )

    def _interaction_counts(self, interactions: list[dict[str, Any]]) -> dict[str, int]:
        counts = {
            "followers_count": 0,
            "following_count": 0,
            "total_likes": 0,
        }
        field_map = {
            "fans": "followers_count",
            "follows": "following_count",
            "interaction": "total_likes",
        }
        for item in interactions:
            key = field_map.get(str(item.get("type") or ""))
            if key:
                counts[key] = int(PostExtractor.normalize_count(item.get("count"))["value"])
        return counts

    @staticmethod
    def _gender(value: Any) -> str:
        if value in (1, "1", "female", "Female"):
            return "Female"
        if value in (0, "0", "male", "Male"):
            return "Male"
        return ""
