"""Shard planner: partition FileManifest lists into token-budget shards."""
from __future__ import annotations

import os
from pathlib import Path

from rekipedia.models.contracts import FileManifest, LLMConfig, Shard

# Rough tokens-per-byte ratio (4 chars ≈ 1 token for code)
_BYTES_PER_TOKEN = 4
# Max tokens per shard before a new shard is started
_DEFAULT_TOKEN_BUDGET = 40_000


class ShardPlanner:
    """Group files into shards that fit within a token budget.

    Files are first grouped by top-level directory.  If a group exceeds the
    budget it is split into consecutive sub-groups.
    """

    def __init__(self, token_budget: int = _DEFAULT_TOKEN_BUDGET) -> None:
        self._budget = int(os.environ.get("REKIPEDIA_SHARD_TOKEN_BUDGET", str(token_budget)))

    def plan(
        self,
        files: list[FileManifest],
        llm: LLMConfig | None = None,
    ) -> list[Shard]:
        if not files:
            return []

        llm = llm or LLMConfig()

        # Group by top-level directory (or "." for root files)
        groups: dict[str, list[FileManifest]] = {}
        for f in files:
            top = Path(f.path).parts[0] if "/" in f.path or "\\" in f.path else "."
            groups.setdefault(top, []).append(f)

        shards: list[Shard] = []
        for group_dir, group_files in groups.items():
            shards.extend(self._split_group(group_dir, group_files, llm))

        return shards

    def _split_group(
        self,
        group_dir: str,
        files: list[FileManifest],
        llm: LLMConfig,
    ) -> list[Shard]:
        shards: list[Shard] = []
        bucket: list[FileManifest] = []
        bucket_tokens = 0
        bucket_idx = 0

        for f in files:
            file_tokens = max(1, f.size_bytes // _BYTES_PER_TOKEN)
            if bucket and bucket_tokens + file_tokens > self._budget:
                shards.append(_make_shard(group_dir, bucket_idx, bucket, llm))
                bucket = []
                bucket_tokens = 0
                bucket_idx += 1
            bucket.append(f)
            bucket_tokens += file_tokens

        if bucket:
            shards.append(_make_shard(group_dir, bucket_idx, bucket, llm))

        return shards


def _make_shard(
    group_dir: str, idx: int, files: list[FileManifest], llm: LLMConfig
) -> Shard:
    shard_id = group_dir if idx == 0 else f"{group_dir}#{idx}"
    return Shard(shard_id=shard_id, root=group_dir, files=files, llm=llm)


class CommunityShardPlanner(ShardPlanner):
    """Shard planner that respects import-graph community structure.

    Files assigned to the same community ID are co-located in the same
    shard *before* the token-budget split kicks in.  This keeps
    semantically related modules together so the LLM sees complete
    context for each tightly coupled cluster.

    Use :py:meth:`plan_with_communities` instead of the inherited
    :py:meth:`plan` when a community map is available.
    """

    def plan_with_communities(
        self,
        files: list[FileManifest],
        community_map: dict[str, int],
        llm: LLMConfig | None = None,
    ) -> list[Shard]:
        """Plan shards respecting community membership.

        Args:
            files: All file manifests to shard.
            community_map: Mapping of file path → community id.
                           Files absent from the map are each placed in
                           their own singleton community.
            llm: Optional LLM config forwarded to each Shard.

        Returns:
            List of Shard objects with community-aware grouping.
            Shard IDs are prefixed with ``community_<id>`` for traceability.
        """
        if not files:
            return []

        llm = llm or LLMConfig()

        # Assign each file to a community; absent files → unique sentinel
        community_groups: dict[int, list[FileManifest]] = {}
        next_singleton = max(community_map.values(), default=-1) + 1
        for f in files:
            if f.path in community_map:
                cid = community_map[f.path]
            else:
                # Treat as own isolated community so it isn't merged with others
                cid = next_singleton
                next_singleton += 1
            community_groups.setdefault(cid, []).append(f)

        # Split each community group by token budget
        shards: list[Shard] = []
        for cid in sorted(community_groups.keys()):
            group = community_groups[cid]
            group_dir = f"community_{cid}"
            shards.extend(self._split_group(group_dir, group, llm))

        return shards
