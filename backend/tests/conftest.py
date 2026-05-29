import os
import shutil
import pytest

@pytest.fixture(scope="session", autouse=True)
def prepare_test_run_fixtures():
    """Set up the isolated fixtures/test_run folder before tests run, and clean it up after."""
    orig_fixtures = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'fixtures'))
    test_run_dir = os.path.join(orig_fixtures, 'test_run')

    # Recreate a clean test_run directory
    if os.path.exists(test_run_dir):
        try:
            shutil.rmtree(test_run_dir)
        except Exception:
            pass

    os.makedirs(test_run_dir, exist_ok=True)

    # Copy original metrics and pipelines to test_run
    for folder in ['metrics', 'pipelines']:
        src = os.path.join(orig_fixtures, folder)
        dst = os.path.join(test_run_dir, folder)
        if os.path.exists(src):
            try:
                shutil.copytree(src, dst)
            except Exception:
                pass

    yield

    # Clean up after test session finishes to leave a clean state
    if os.path.exists(test_run_dir):
        try:
            shutil.rmtree(test_run_dir)
        except Exception:
            pass
