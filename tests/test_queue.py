import sys
from pathlib import Path
import pytest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestQueueDB:

    @pytest.fixture(autouse=True)
    def setup_test_db(self, tmp_path):
        # Patch path DB ke temporary directory
        test_db_path = tmp_path / "test_queue.db"
        with patch("db.DB_PATH", test_db_path):
            import db

            db.init_db()
            yield db
            # Cleanup
            if test_db_path.exists():
                test_db_path.unlink()

    def test_add_job(self):
        import db

        job_id = db.add_job(
            url="https://youtube.com/watch?v=test",
            content_type="podcast",
            max_clips=3,
            lang="id",
            discord_channel_id=12345,
        )
        assert job_id == 1

        status = db.get_queue_status()
        assert status["pending"] == 1
        assert status["processing"] == 0

    def test_fifo_order(self):
        import db

        id1 = db.add_job(url="url1")
        id2 = db.add_job(url="url2")

        job = db.get_next_pending_job()
        assert job["id"] == id1
        assert job["url"] == "url1"

        db.update_job_status(id1, "processing")

        next_job = db.get_next_pending_job()
        assert next_job["id"] == id2
        assert next_job["url"] == "url2"

    def test_update_status(self):
        import db

        job_id = db.add_job(url="test_url")
        db.update_job_status(job_id, "processing")

        status = db.get_queue_status()
        assert status["pending"] == 0
        assert status["processing"] == 1

        db.update_job_status(job_id, "completed")
        status = db.get_queue_status()
        assert status["processing"] == 0
        assert status["completed"] == 1

        db.update_job_status(job_id, "failed", error_message="some error")
        status = db.get_queue_status()
        assert status["completed"] == 0
        assert status["failed"] == 1
