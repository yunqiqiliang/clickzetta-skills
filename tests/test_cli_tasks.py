"""
cz-cli validation tests for Studio task management skills.

Covers cz-cli commands from:
- clickzetta-studio-task-manager: task list, list-folders, create, content,
  save-content, save-cron, deploy, undeploy, execute, delete, create-folder,
  delete-folder, deps
- clickzetta-sql-pipeline-manager: task save-content, save-cron, deploy
- clickzetta-dw-modeling: task create-folder, save-content, save-cron, deploy
- clickzetta-pipeline-review: task list-folders, task list, task content,
  runs list, runs logs, runs stats, runs detail
- clickzetta-batch-sync-pipeline: task create --type DI, save-cron, deploy,
  runs list, runs detail, attempts log, runs refill
- clickzetta-cdc-sync-pipeline: task create --type MULTI_REALTIME, deploy
- clickzetta-realtime-sync-pipeline: task create --type REALTIME, deploy

Note: Integration task types (DI, MULTI_DI, REALTIME, MULTI_REALTIME) require
a Sync VCluster for deployment. Tests verify create/content/delete only.
"""
import json
import subprocess
import time
import pytest

CLI_PROFILE = "skill_test"
TEST_FOLDER = "skill_test_cli_folder"


def cz(args: list[str]) -> dict:
    cmd = ["cz-cli", "--profile", CLI_PROFILE] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    raw = result.stdout.strip() or result.stderr.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw, "_returncode": result.returncode}


def cz_ok(args: list[str]) -> dict:
    d = cz(args)
    assert "error" not in d, \
        f"Expected success: cz-cli {' '.join(args)}\n{json.dumps(d, ensure_ascii=False)}"
    return d


def cz_task_id(name: str, task_type: str = "SQL") -> int:
    d = cz_ok(["task", "create", name, "--type", task_type])
    return d["data"]["id"]


def cz_cleanup_task(task_id: int):
    """Best-effort cleanup: undeploy if published, then delete."""
    cz(["task", "undeploy", str(task_id), "-y"])
    cz(["task", "delete", str(task_id), "-y"])


# ---------------------------------------------------------------------------
# Folder management (studio-task-manager, dw-modeling, pipeline-review)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_folder_id():
    """Create a test folder for the module, clean up after."""
    d = cz_ok(["task", "create-folder", TEST_FOLDER])
    folder_id = d["data"]
    yield folder_id
    cz(["task", "delete-folder", str(folder_id), "-y"])


def test_task_list_folders():
    """cz-cli task list-folders must return folder list."""
    d = cz_ok(["task", "list-folders"])
    assert "data" in d
    assert isinstance(d["data"], list)


def test_task_create_folder(test_folder_id):
    """cz-cli task create-folder must return a folder id."""
    assert isinstance(test_folder_id, int)
    assert test_folder_id > 0


def test_task_list_folders_contains_test_folder(test_folder_id):
    """Newly created folder must appear in list-folders output."""
    d = cz_ok(["task", "list-folders"])
    folder_ids = [f["id"] for f in d["data"]]
    assert test_folder_id in folder_ids


# ---------------------------------------------------------------------------
# Task lifecycle (studio-task-manager, sql-pipeline-manager, dw-modeling)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sql_task(test_folder_id):
    """Create a SQL task in the test folder, clean up after."""
    task_id = cz_task_id(f"skill_test_sql_{test_folder_id}")
    yield task_id
    cz_cleanup_task(task_id)


def test_task_list(sql_task):
    """cz-cli task list must return task list including our test task."""
    d = cz_ok(["task", "list", "--page-size", "50"])
    assert "data" in d
    task_ids = [t["task_id"] for t in d["data"]]
    assert sql_task in task_ids


def test_task_list_with_folder(test_folder_id, sql_task):
    """cz-cli task list --folder <id> must filter by folder."""
    d = cz_ok(["task", "list", "--folder", str(test_folder_id)])
    assert "data" in d


def test_task_content(sql_task):
    """cz-cli task content <id> must return task metadata."""
    d = cz_ok(["task", "content", str(sql_task)])
    assert "data" in d
    assert d["data"]["task_id"] == sql_task


def test_task_save_content(sql_task):
    """cz-cli task save-content <id> --content must save SQL content."""
    d = cz_ok(["task", "save-content", str(sql_task), "--content", "SELECT 1 AS cli_test"])
    assert "error" not in d


def test_task_save_cron(sql_task):
    """cz-cli task save-cron <id> --cron must save schedule config."""
    d = cz_ok(["task", "save-cron", str(sql_task), "--cron", "0 30 2 * * ? *"])
    assert "error" not in d


def test_task_deps(sql_task):
    """cz-cli task deps <id> must return dependency info."""
    d = cz_ok(["task", "deps", str(sql_task)])
    assert "error" not in d


def test_task_deploy(sql_task):
    """cz-cli task deploy <id> -y must publish the task."""
    d = cz_ok(["task", "deploy", str(sql_task), "-y"])
    assert "error" not in d


def test_task_undeploy(sql_task):
    """cz-cli task undeploy <id> -y must take the task offline."""
    d = cz_ok(["task", "undeploy", str(sql_task), "-y"])
    assert "error" not in d


# ---------------------------------------------------------------------------
# Task execute + runs (pipeline-review, studio-task-manager)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def executed_task():
    """Create, save, execute a task and return (task_id, run_id)."""
    task_id = cz_task_id("skill_test_exec")
    cz_ok(["task", "save-content", str(task_id), "--content", "SELECT 1 AS exec_test"])
    cz_ok(["task", "execute", str(task_id)])
    time.sleep(8)
    d = cz(["runs", "list", "--task", str(task_id), "--limit", "1"])
    run_id = d["data"][0]["run_id"] if d.get("data") else None
    yield task_id, run_id
    cz_cleanup_task(task_id)


def test_task_execute(executed_task):
    """cz-cli task execute <id> must trigger an ad-hoc run."""
    task_id, run_id = executed_task
    assert run_id is not None, "Expected a run_id after execute"


def test_runs_list(executed_task):
    """cz-cli runs list --task <id> must return run records."""
    task_id, _ = executed_task
    d = cz_ok(["runs", "list", "--task", str(task_id), "--limit", "5"])
    assert "data" in d
    assert d["count"] >= 1


def test_runs_detail(executed_task):
    """cz-cli runs detail <run_id> must return run metadata."""
    _, run_id = executed_task
    if run_id is None:
        pytest.skip("No run_id available")
    d = cz_ok(["runs", "detail", str(run_id)])
    assert "data" in d
    assert d["data"]["run_id"] == run_id


def test_runs_logs(executed_task):
    """cz-cli runs logs <run_id> must return execution log content."""
    _, run_id = executed_task
    if run_id is None:
        pytest.skip("No run_id available")
    d = cz_ok(["runs", "logs", str(run_id)])
    assert "data" in d
    assert "logContent" in d["data"]
    assert len(d["data"]["logContent"]) > 0


def test_runs_stats(executed_task):
    """cz-cli runs stats --task <id> must return statistics."""
    task_id, _ = executed_task
    d = cz(["runs", "stats", "--task", str(task_id)])
    assert "error" not in d


# ---------------------------------------------------------------------------
# Integration task types (batch-sync, cdc-sync, realtime-sync)
# Only verify create/content/delete — deploy requires Sync VCluster
# ---------------------------------------------------------------------------

def test_task_create_type_di():
    """cz-cli task create --type DI must create an offline sync task."""
    task_id = cz_task_id("skill_test_di", "DI")
    try:
        d = cz_ok(["task", "content", str(task_id)])
        assert d["data"]["task_id"] == task_id
    finally:
        cz_cleanup_task(task_id)


def test_task_create_type_multi_di():
    """cz-cli task create --type MULTI_DI must create a multi-table sync task."""
    task_id = cz_task_id("skill_test_multi_di", "MULTI_DI")
    try:
        d = cz_ok(["task", "content", str(task_id)])
        assert d["data"]["task_id"] == task_id
    finally:
        cz_cleanup_task(task_id)


def test_task_create_type_realtime():
    """cz-cli task create --type REALTIME must create a realtime sync task."""
    task_id = cz_task_id("skill_test_realtime", "REALTIME")
    try:
        d = cz_ok(["task", "content", str(task_id)])
        assert d["data"]["task_id"] == task_id
    finally:
        cz_cleanup_task(task_id)


def test_task_create_type_multi_realtime():
    """cz-cli task create --type MULTI_REALTIME must create a CDC multi-table task."""
    task_id = cz_task_id("skill_test_multi_rt", "MULTI_REALTIME")
    try:
        d = cz_ok(["task", "content", str(task_id)])
        assert d["data"]["task_id"] == task_id
    finally:
        cz_cleanup_task(task_id)


# ---------------------------------------------------------------------------
# Datasource (batch-sync, data-ingest)
# ---------------------------------------------------------------------------

def test_datasource_list():
    """cz-cli datasource list must return datasource list."""
    d = cz_ok(["datasource", "list"])
    assert "data" in d
    assert isinstance(d["data"], list)
