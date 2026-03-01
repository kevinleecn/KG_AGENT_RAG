#!/usr/bin/env python3
"""
Test progress system functionality.
"""

import os
import sys
import tempfile
import shutil
import time

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from src.progress_manager import ProgressManager, TaskType, TaskStatus, ProgressState


def test_progress_manager():
    """Test basic ProgressManager functionality"""
    print("Testing ProgressManager...")

    # Create temporary directory for test data
    test_dir = tempfile.mkdtemp(prefix="progress_test_")
    print(f"Test directory: {test_dir}")

    try:
        # Initialize progress manager
        pm = ProgressManager(test_dir)

        # Test creating a task
        task_id = pm.create_task(
            filename="test.pdf",
            task_type=TaskType.PARSE,
            total_steps=100,
            metadata={"test": True}
        )
        print(f"Created task: {task_id}")

        # Test getting task state
        state = pm.get_task_state(task_id)
        assert state is not None
        assert state.task_id == task_id
        assert state.filename == "test.pdf"
        assert state.task_type == TaskType.PARSE
        assert state.status == TaskStatus.PENDING
        assert state.progress == 0.0
        print(f"Task state retrieved: {state.status}")

        # Test updating progress
        success = pm.update_progress(
            task_id=task_id,
            current_step=25,
            step_description="Parsing pages",
            message="Processing first 25 pages"
        )
        assert success
        print("Progress updated to 25%")

        # Check updated state
        state = pm.get_task_state(task_id)
        assert state.status == TaskStatus.RUNNING
        assert state.progress == 0.25
        assert state.current_step == 25
        assert state.step_description == "Parsing pages"

        # Test completing task
        result = {"pages_parsed": 100, "text_length": 5000}
        success = pm.complete_task(task_id, result, "Parsing completed successfully")
        assert success
        print("Task marked as completed")

        # Check completed state
        state = pm.get_task_state(task_id)
        assert state.status == TaskStatus.COMPLETED
        assert state.progress == 1.0
        assert state.result == result

        # Test getting all tasks
        tasks = pm.get_all_tasks()
        assert len(tasks) == 1
        print(f"Total tasks: {len(tasks)}")

        # Test task statistics
        stats = pm.get_task_stats()
        assert stats['total_tasks'] == 1
        assert stats['status_counts']['completed'] == 1
        print(f"Task stats: {stats}")

        # Test cleanup of old tasks (should not clean up recent tasks)
        cleaned = pm.cleanup_old_tasks(max_age_hours=0.001)  # 3.6 seconds
        assert cleaned == 0  # Task too recent
        print(f"Cleaned {cleaned} old tasks")

        # Test deleting task
        success = pm.delete_task(task_id)
        assert success
        print("Task deleted")

        # Verify task is gone
        state = pm.get_task_state(task_id)
        assert state is None

        print("All ProgressManager tests passed!")

    finally:
        # Clean up test directory
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"Cleaned up test directory: {test_dir}")


def test_progress_state_serialization():
    """Test ProgressState serialization/deserialization"""
    print("\nTesting ProgressState serialization...")

    # Create a ProgressState
    original = ProgressState(
        task_id="test-id",
        filename="test.pdf",
        task_type=TaskType.PARSE,
        status=TaskStatus.RUNNING,
        progress=0.5,
        total_steps=100,
        current_step=50,
        step_description="Parsing",
        message="Halfway there",
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:01:00",
        metadata={"page": 25},
        result=None,
        error=None
    )

    # Convert to dict and back
    state_dict = original.to_dict()
    restored = ProgressState.from_dict(state_dict)

    # Check that important fields match
    assert restored.task_id == original.task_id
    assert restored.filename == original.filename
    assert restored.task_type == original.task_type
    assert restored.status == original.status
    assert restored.progress == original.progress
    assert restored.current_step == original.current_step
    assert restored.step_description == original.step_description

    print("ProgressState serialization test passed!")


if __name__ == "__main__":
    try:
        test_progress_state_serialization()
        test_progress_manager()
        print("\n✅ All progress system tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)