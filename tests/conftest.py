"""pytest configuration for ExFlow Enterprise."""
import os
import sys
import tempfile

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Use a temp DB for tests so we never touch real data
TEST_DB_DIR = tempfile.mkdtemp(prefix="exflow_test_")
os.environ["EXFLOW_TEST_DB"] = os.path.join(TEST_DB_DIR, "test.db")
os.environ["EXFLOW_ADMIN_PW"] = "test-admin-pass"
