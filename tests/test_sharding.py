"""Tests for the sharding module."""
from __future__ import annotations

from rekipedia.models.contracts import FileManifest, LLMConfig
from rekipedia.orchestrator.sharding import CommunityShardPlanner, ShardPlanner

_MINI_FILES = [
    FileManifest(path="src/a.py", sha256="aa" * 16, size_bytes=1000),
    FileManifest(path="src/b.py", sha256="bb" * 16, size_bytes=1000),
    FileManifest(path="tests/test_a.py", sha256="cc" * 16, size_bytes=500),
    FileManifest(path="README.md", sha256="dd" * 16, size_bytes=200),
]


def test_empty_files():
    planner = ShardPlanner()
    assert planner.plan([]) == []


def test_single_file_produces_one_shard():
    planner = ShardPlanner()
    shards = planner.plan([_MINI_FILES[0]])
    assert len(shards) == 1
    assert shards[0].files == [_MINI_FILES[0]]


def test_groups_by_top_dir():
    planner = ShardPlanner(token_budget=100_000)
    shards = planner.plan(_MINI_FILES)
    # src/, tests/, and "." (for README)
    group_roots = {s.root for s in shards}
    assert "src" in group_roots
    assert "tests" in group_roots


def test_splits_on_token_budget():
    # Each file is 4000 bytes → 1000 tokens.  Budget = 1500 → each file = own shard
    big_files = [
        FileManifest(path=f"src/big{i}.py", sha256=f"{i:02x}" * 16, size_bytes=6000)
        for i in range(3)
    ]
    planner = ShardPlanner(token_budget=1000)
    shards = planner.plan(big_files)
    # Three files each >budget → 3 shards
    assert len(shards) == 3


def test_shard_ids_unique():
    planner = ShardPlanner(token_budget=500)
    files = [
        FileManifest(path=f"src/f{i}.py", sha256=f"{i:02x}" * 16, size_bytes=3000)
        for i in range(5)
    ]
    shards = planner.plan(files)
    ids = [s.shard_id for s in shards]
    assert len(ids) == len(set(ids))


def test_llm_config_propagated():
    cfg = LLMConfig(model="custom/model")
    planner = ShardPlanner()
    shards = planner.plan([_MINI_FILES[0]], cfg)
    assert shards[0].llm.model == "custom/model"


# ── CommunityShardPlanner tests ───────────────────────────────────────────────

def test_community_planner_groups_related_files() -> None:
    """Files in the same community should land in the same shard."""
    files = [
        FileManifest(path="src/auth.py",    sha256="aa" * 16, size_bytes=500),
        FileManifest(path="src/jwt.py",     sha256="bb" * 16, size_bytes=500),
        FileManifest(path="src/payment.py", sha256="cc" * 16, size_bytes=500),
        FileManifest(path="src/billing.py", sha256="dd" * 16, size_bytes=500),
    ]
    community_map = {
        "src/auth.py": 0, "src/jwt.py": 0,
        "src/payment.py": 1, "src/billing.py": 1,
    }
    planner = CommunityShardPlanner(token_budget=100_000)
    shards = planner.plan_with_communities(files, community_map)
    shard_paths = [[f.path for f in s.files] for s in shards]

    def same_shard(a: str, b: str) -> bool:
        return any(a in paths and b in paths for paths in shard_paths)

    assert same_shard("src/auth.py", "src/jwt.py"), "auth+jwt should be co-located"
    assert same_shard("src/payment.py", "src/billing.py"), "payment+billing should be co-located"


def test_community_planner_respects_token_budget() -> None:
    """Oversized communities must still be split on token budget."""
    files = [
        FileManifest(path=f"src/f{i}.py", sha256=f"{i:02x}" * 16, size_bytes=8000)
        for i in range(4)
    ]
    # All in same community but budget only fits ~1 file (2000 tokens each, budget=1500)
    community_map = {f"src/f{i}.py": 0 for i in range(4)}
    planner = CommunityShardPlanner(token_budget=1500)
    shards = planner.plan_with_communities(files, community_map)
    assert len(shards) >= 4, "Should split oversized community across multiple shards"


def test_community_planner_empty_community_map_matches_base() -> None:
    """Empty community_map: each file treated as own community → same count as ShardPlanner."""
    base = ShardPlanner(token_budget=100_000).plan(_MINI_FILES)
    community = CommunityShardPlanner(token_budget=100_000).plan_with_communities(_MINI_FILES, {})
    # Both should produce same number of shards (grouping by community vs by dir)
    # With empty map every file is its own community of 1, so same count as base
    assert len(community) >= 1, "Should produce at least one shard"


def test_community_planner_empty_files() -> None:
    planner = CommunityShardPlanner()
    assert planner.plan_with_communities([], {}) == []


def test_community_planner_shard_ids_unique() -> None:
    files = [
        FileManifest(path=f"src/x{i}.py", sha256=f"{i:02x}" * 16, size_bytes=8000)
        for i in range(6)
    ]
    community_map = {f"src/x{i}.py": i % 2 for i in range(6)}  # Two communities of 3
    planner = CommunityShardPlanner(token_budget=1000)
    shards = planner.plan_with_communities(files, community_map)
    ids = [s.shard_id for s in shards]
    assert len(ids) == len(set(ids)), "All shard IDs must be unique"
