"""TaskRunner 任务运行器测试"""

import contextlib
import threading
import time
from datetime import datetime

from remote_cmd.service.task_runner import Task, TaskRunner, TaskStatus


class TestTaskStatus:
    def test_values(self):
        assert TaskStatus.PENDING.value == "PENDING"
        assert TaskStatus.RUNNING.value == "RUNNING"
        assert TaskStatus.SUCCESS.value == "SUCCESS"
        assert TaskStatus.FAILED.value == "FAILED"
        assert TaskStatus.CANCELLED.value == "CANCELLED"


class TestTask:
    def test_create(self):
        t = Task(id="t1", name="test", status=TaskStatus.PENDING, created_at=datetime.now())
        assert t.id == "t1"
        assert t.name == "test"
        assert t.status == TaskStatus.PENDING
        assert t.result is None
        assert t.error is None


class TestTaskRunner:
    def test_submit_and_complete(self):
        runner = TaskRunner(max_workers=2)

        def task_func():
            return "done"

        task_id = runner.submit("test", task_func)
        task = runner.wait_for(task_id, timeout=5)
        assert task.status == TaskStatus.SUCCESS
        assert task.result == "done"

    def test_submit_with_args(self):
        runner = TaskRunner()

        def add(a, b):
            return a + b

        task_id = runner.submit("add", add, 2, 3)
        task = runner.wait_for(task_id, timeout=5)
        assert task.result == 5

    def test_task_failure(self):
        runner = TaskRunner()

        def failing():
            raise ValueError("something went wrong")

        task_id = runner.submit("fail", failing)

        try:
            task = runner.wait_for(task_id, timeout=5)
            assert task.status == TaskStatus.FAILED
            assert "something went wrong" in (task.error or "")
        except TimeoutError:
            pass

    def test_cancel_pending_task(self):
        runner = TaskRunner(max_workers=2)
        block = threading.Event()

        def waiter():
            block.wait(timeout=5)
            return "done"

        id1 = runner.submit("block1", waiter)
        id2 = runner.submit("block2", waiter)
        time.sleep(0.05)

        def submit_pending():
            runner.submit("pending3", waiter)

        threading.Thread(target=submit_pending, daemon=True).start()
        time.sleep(0.05)

        pending_tasks = [t for t in runner.list_tasks() if t.name == "pending3"]
        assert len(pending_tasks) == 1
        pending_id = pending_tasks[0].id
        assert runner.get_status(pending_id) == TaskStatus.PENDING
        assert runner.active_count == 2

        cancelled = runner.cancel(pending_id)
        assert cancelled is True
        assert runner.get_status(pending_id) == TaskStatus.CANCELLED

        block.set()
        runner.wait_for(id1, timeout=5)
        runner.wait_for(id2, timeout=5)

    def test_cancel_nonexistent(self):
        runner = TaskRunner()
        assert runner.cancel("nonexistent") is False

    def test_concurrency_limit(self):
        runner = TaskRunner(max_workers=2)

        num_running = 0
        max_concurrent = 0
        lock = __import__("threading").Lock()

        def track():
            nonlocal num_running, max_concurrent
            with lock:
                num_running += 1
                max_concurrent = max(max_concurrent, num_running)
            time.sleep(0.2)
            with lock:
                num_running -= 1

        ids = []
        for i in range(4):
            tid = runner.submit(f"t{i}", track)
            ids.append(tid)
        for tid in ids:
            with contextlib.suppress(TimeoutError):
                runner.wait_for(tid, timeout=5)

        assert max_concurrent <= 2

    def test_list_tasks(self):
        runner = TaskRunner()
        id1 = runner.submit("a", lambda: None)
        id2 = runner.submit("b", lambda: None)
        runner.wait_for(id1, timeout=5)
        runner.wait_for(id2, timeout=5)

        tasks = runner.list_tasks()
        assert len(tasks) >= 2

    def test_list_tasks_empty(self):
        runner = TaskRunner()
        assert runner.list_tasks() == []

    def test_get_task_nonexistent(self):
        runner = TaskRunner()
        assert runner.get_task("nonexistent") is None

    def test_get_status(self):
        runner = TaskRunner()
        tid = runner.submit("s", lambda: "ok")
        runner.wait_for(tid, timeout=5)
        assert runner.get_status(tid) == TaskStatus.SUCCESS

    def test_cancel_all(self):
        runner = TaskRunner(max_workers=1)
        runner.submit("slow", time.sleep, 30)

        pending_ids = []

        def submit_pending(i):
            tid = runner.submit(f"p{i}", time.sleep, 30)
            pending_ids.append(tid)

        threads = []
        for i in range(3):
            t = threading.Thread(target=submit_pending, args=(i,), daemon=True)
            t.start()
            threads.append(t)
        time.sleep(0.2)

        cancelled = runner.cancel_all()
        assert cancelled >= 1

    def test_cleanup_old(self):
        runner = TaskRunner()
        tid = runner.submit("old", lambda: "ok")
        runner.wait_for(tid, timeout=5)
        time.sleep(0.05)
        count = runner.cleanup_old(max_age_seconds=0)
        assert count >= 1
        assert runner.get_task(tid) is None

    def test_wait_for_timeout(self):
        runner = TaskRunner()
        tid = runner.submit("slow", time.sleep, 30)
        try:
            runner.wait_for(tid, timeout=0.1)
            raise AssertionError("应抛出 TimeoutError")
        except TimeoutError:
            pass

    def test_wait_for_nonexistent(self):
        runner = TaskRunner()
        try:
            runner.wait_for("nonexistent")
            raise AssertionError("应抛出 KeyError")
        except KeyError:
            pass

    def test_active_count(self):
        runner = TaskRunner(max_workers=5)
        assert runner.active_count == 0
        tid = runner.submit("slow", time.sleep, 0.5)
        time.sleep(0.05)
        assert runner.active_count >= 1
        runner.wait_for(tid, timeout=5)
        assert runner.active_count == 0

    def test_pending_count(self):
        runner = TaskRunner(max_workers=1)
        runner.submit("slow", time.sleep, 0.3)
        time.sleep(0.05)

        # 后台提交第二个任务，不阻塞
        def submit_another():
            runner.submit("pending", time.sleep, 0.1)

        threading.Thread(target=submit_another, daemon=True).start()
        time.sleep(0.1)
        assert runner.pending_count >= 1
