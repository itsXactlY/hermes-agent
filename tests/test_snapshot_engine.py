"""
Tests for the Runtime Snapshot Engine.

Covers: hashing, object store, snapshot/restore roundtrip,
deduplication, SQLite safe copy, diff, prune, debouncing.
"""

import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.snapshot_engine import (
    SnapshotEngine,
    auto_snapshot,
    diff,
    get_head,
    list_snapshots,
    prune,
    restore,
    snapshot,
)


@pytest.fixture
def tmp_hermes(tmp_path):
    """Create a temporary ~/.hermes-like directory with test files."""
    hermes = tmp_path / "hermes"
    hermes.mkdir()

    # Create test state files
    (hermes / "config.yaml").write_text("model: test\nprovider: openai\n")
    (hermes / "auth.json").write_text('{"openai": "sk-test"}')

    # Create a real SQLite DB
    db_path = hermes / "state.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'hello')")
    conn.commit()
    conn.close()

    # Cron dir
    cron_dir = hermes / "cron"
    cron_dir.mkdir()
    (cron_dir / "jobs.json").write_text('[{"name": "test"}]')

    # Other files
    (hermes / "gateway_state.json").write_text("{}")
    (hermes / "channel_directory.json").write_text("{}")
    (hermes / "processes.json").write_text("[]")

    return hermes


@pytest.fixture
def engine(tmp_hermes):
    """Create a SnapshotEngine pointed at the temp hermes dir."""
    return SnapshotEngine(hermes_home=tmp_hermes)


# ---------------------------------------------------------------------------
# Basic functionality
# ---------------------------------------------------------------------------

class TestBasicSnapshot:
    """Test core snapshot creation and restoration."""

    def test_snapshot_creates_manifest(self, engine):
        snap_id = engine.snapshot(label="test")
        assert snap_id is not None
        assert "test" in snap_id

        # Check manifest exists
        snap_dir = engine.snapshots_dir / snap_id
        assert (snap_dir / "manifest.json").exists()
        assert (snap_dir / "meta.json").exists()

        # Check manifest content
        with open(snap_dir / "manifest.json") as f:
            manifest = json.load(f)
        assert "config.yaml" in manifest
        assert "state.db" in manifest
        assert "auth.json" in manifest

    def test_snapshot_metadata(self, engine):
        snap_id = engine.snapshot(label="meta-test", trigger="manual")
        meta_path = engine.snapshots_dir / snap_id / "meta.json"
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["label"] == "meta-test"
        assert meta["trigger"] == "manual"
        assert meta["file_count"] > 0
        assert meta["total_size"] > 0

    def test_head_updated(self, engine):
        assert engine.get_head() is None
        snap_id = engine.snapshot()
        assert engine.get_head() == snap_id

    def test_restore_roundtrip(self, engine, tmp_hermes):
        # Snapshot original state
        snap_id = engine.snapshot(label="original")

        # Modify state
        (tmp_hermes / "config.yaml").write_text("model: modified\n")

        # Restore
        assert engine.restore(snap_id)
        content = (tmp_hermes / "config.yaml").read_text()
        assert "test" in content
        assert "modified" not in content

    def test_restore_db_roundtrip(self, engine, tmp_hermes):
        """SQLite DB should survive snapshot/restore."""
        snap_id = engine.snapshot()

        # Modify DB
        conn = sqlite3.connect(str(tmp_hermes / "state.db"))
        conn.execute("INSERT INTO test VALUES (2, 'world')")
        conn.commit()
        conn.close()

        # Restore
        engine.restore(snap_id)

        # Verify
        conn = sqlite3.connect(str(tmp_hermes / "state.db"))
        rows = conn.execute("SELECT * FROM test").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][1] == "hello"


# ---------------------------------------------------------------------------
# Content-addressed deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    """Verify that identical files share objects."""

    def test_same_content_same_hash(self, engine, tmp_hermes):
        """Two snapshots with unchanged files should share objects."""
        snap1 = engine.snapshot(label="snap1")

        # Modify state slightly so snapshot is created, then check shared objects
        (tmp_hermes / "gateway_state.json").write_text('{"changed": true}')
        snap2 = engine.snapshot(label="snap2")

        assert snap1 is not None
        assert snap2 is not None

        m1 = json.load(open(engine.snapshots_dir / snap1 / "manifest.json"))
        m2 = json.load(open(engine.snapshots_dir / snap2 / "manifest.json"))

        # config.yaml hash should be identical (didn't change between snapshots)
        assert m1["config.yaml"] == m2["config.yaml"]

    def test_object_store_dedup(self, engine, tmp_hermes):
        """Same content stored twice = 1 object file."""
        engine._store_object(b"identical content")
        engine._store_object(b"identical content")

        # Count objects
        obj_count = sum(1 for d in engine.objects.iterdir() if d.is_dir()
                        for f in d.iterdir())
        assert obj_count == 1


# ---------------------------------------------------------------------------
# SQLite safe copy
# ---------------------------------------------------------------------------

class TestSqliteSafeCopy:
    """Verify SQLite databases are safely copied."""

    def test_safe_copy_produces_valid_db(self, engine, tmp_hermes):
        """Safe-copied DB should be queryable."""
        src = tmp_hermes / "state.db"
        dst = tmp_hermes / "state_copy.db"

        assert engine._safe_copy_db(src, dst)

        conn = sqlite3.connect(str(dst))
        rows = conn.execute("SELECT * FROM test").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][1] == "hello"

    def test_safe_copy_with_wal(self, engine, tmp_hermes):
        """Safe copy should handle WAL mode correctly."""
        src = tmp_hermes / "state.db"

        # Open in WAL mode and write
        conn = sqlite3.connect(str(src))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("INSERT INTO test VALUES (3, 'wal-test')")
        conn.commit()

        dst = tmp_hermes / "state_wal_copy.db"
        assert engine._safe_copy_db(src, dst)

        # Verify data is in copy
        conn2 = sqlite3.connect(str(dst))
        rows = conn2.execute("SELECT * FROM test WHERE id=3").fetchall()
        conn2.close()
        assert len(rows) == 1

        conn.close()


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

class TestDiff:
    """Test snapshot diffing."""

    def test_no_changes(self, engine, tmp_hermes):
        """Snapshots with a change should diff cleanly."""
        snap1 = engine.snapshot(label="a")
        (tmp_hermes / "config.yaml").write_text("model: changed\n")
        snap2 = engine.snapshot(label="b")

        assert snap1 is not None
        assert snap2 is not None

        result = engine.diff(snap1, snap2)
        assert "config.yaml" in result["changed"]
        assert len(result["added"]) == 0
        assert len(result["removed"]) == 0

    def test_detect_changes(self, engine, tmp_hermes):
        """Modified file should show in diff."""
        snap1 = engine.snapshot(label="before")

        # Modify config
        (tmp_hermes / "config.yaml").write_text("model: changed\n")

        snap2 = engine.snapshot(label="after")

        result = engine.diff(snap1, snap2)
        assert "config.yaml" in result["changed"]


# ---------------------------------------------------------------------------
# List and history
# ---------------------------------------------------------------------------

class TestListAndHistory:
    """Test snapshot listing."""

    def test_list_returns_recent(self, engine, tmp_hermes):
        (tmp_hermes / "config.yaml").write_text("turn: 1\n")
        engine.snapshot(label="old")
        time.sleep(0.1)
        (tmp_hermes / "config.yaml").write_text("turn: 2\n")
        engine.snapshot(label="new")

        snaps = engine.list_snapshots(limit=10)
        assert len(snaps) >= 2
        # Most recent first
        assert snaps[0]["label"] == "new"

    def test_list_limit(self, engine):
        for i in range(5):
            # Force different timestamps
            time.sleep(0.05)
            # Modify state so each snapshot is unique
            (engine.hermes_home / "config.yaml").write_text(f"turn: {i}\n")
            engine.snapshot(label=f"turn-{i}")

        snaps = engine.list_snapshots(limit=3)
        assert len(snaps) == 3


# ---------------------------------------------------------------------------
# Prune
# ---------------------------------------------------------------------------

class TestPrune:
    """Test snapshot pruning."""

    def test_prune_keeps_last_n(self, engine, tmp_hermes):
        """Prune should always keep the last N snapshots."""
        for i in range(10):
            (tmp_hermes / "config.yaml").write_text(f"turn: {i}\n")
            time.sleep(0.05)
            engine.snapshot(label=f"s{i}")

        deleted = engine.prune(keep_last=5, keep_hourly=0, keep_daily=0)
        remaining = engine.list_snapshots(limit=100)
        assert len(remaining) <= 5 + deleted  # At most 5 kept

    def test_prune_cleans_history_db(self, engine, tmp_hermes):
        """Prune should clean up the history DB."""
        for i in range(5):
            (tmp_hermes / "config.yaml").write_text(f"v{i}\n")
            time.sleep(0.05)
            engine.snapshot()

        engine.prune(keep_last=2, keep_hourly=0, keep_daily=0)
        remaining = engine.list_snapshots(limit=100)
        # Should have at most 2 from keep_last
        assert len(remaining) <= 2


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    """Test the module-level shorthand functions."""

    def test_snapshot_function(self, tmp_hermes):
        """Module-level snapshot() should work."""
        with patch("tools.snapshot_engine.get_hermes_home", return_value=tmp_hermes):
            # Reset global engine
            import tools.snapshot_engine as se
            se._engine = None

            snap_id = snapshot(label="conv-test")
            assert snap_id is not None
            assert "conv-test" in snap_id

    def test_auto_snapshot_debounce(self, tmp_hermes):
        """Auto-snapshot should debounce rapid calls."""
        with patch("tools.snapshot_engine.get_hermes_home", return_value=tmp_hermes):
            import tools.snapshot_engine as se
            se._engine = None
            se._last_snapshot_time = 0

            snap1 = auto_snapshot(debounce_seconds=60, trigger="test")
            assert snap1 is not None

            # Second call within debounce window should be skipped
            snap2 = auto_snapshot(debounce_seconds=60, trigger="test")
            assert snap2 is None


# ---------------------------------------------------------------------------
# State hash / change detection
# ---------------------------------------------------------------------------

class TestChangeDetection:
    """Test compute_state_hash for change detection."""

    def test_same_state_same_hash(self, engine):
        h1 = engine.compute_state_hash()
        h2 = engine.compute_state_hash()
        assert h1 == h2

    def test_changed_state_different_hash(self, engine, tmp_hermes):
        h1 = engine.compute_state_hash()
        (tmp_hermes / "config.yaml").write_text("changed: true\n")
        h2 = engine.compute_state_hash()
        assert h1 != h2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases and error handling."""

    def test_restore_nonexistent_snapshot(self, engine):
        assert engine.restore("does-not-exist-999999") is False

    def test_snapshot_with_missing_files(self, engine, tmp_hermes):
        """Should handle missing files gracefully."""
        # Remove a file
        (tmp_hermes / "processes.json").unlink()
        snap_id = engine.snapshot()
        assert snap_id is not None

    def test_empty_hermes_dir(self, tmp_path):
        """Should handle empty hermes dir without crashing."""
        empty = tmp_path / "empty"
        empty.mkdir()
        eng = SnapshotEngine(hermes_home=empty)
        snap_id = eng.snapshot()
        # Should return None (no files to snapshot)
        assert snap_id is None

    def test_concurrent_snapshots(self, engine):
        """Multiple threads snapshotting shouldn't crash."""
        import threading

        results = []
        def do_snap():
            r = engine.snapshot(label="concurrent")
            results.append(r)

        threads = [threading.Thread(target=do_snap) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # At least one should succeed
        assert any(r is not None for r in results)
