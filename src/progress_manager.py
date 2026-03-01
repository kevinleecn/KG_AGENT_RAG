"""
Progress Manager for tracking parsing task progress.

This module provides a ProgressManager class that manages parsing task progress
states with thread-safe operations and persistence to disk.
"""

import os
import json
import threading
import uuid
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Status of a parsing task"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Type of task"""
    PARSE = "parse"  # Document parsing
    EXTRACT = "extract"  # Knowledge extraction
    BUILD_GRAPH = "build_graph"  # Graph building
    FULL_PROCESS = "full_process"  # Parse + extract + build graph


@dataclass
class ProgressState:
    """Represents the progress state of a task"""
    task_id: str
    filename: str
    task_type: TaskType
    status: TaskStatus
    progress: float  # 0.0 to 1.0
    total_steps: int
    current_step: int
    step_description: str
    message: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        data['task_type'] = self.task_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressState':
        """Create from dictionary"""
        data['status'] = TaskStatus(data['status'])
        data['task_type'] = TaskType(data['task_type'])
        return cls(**data)


class ProgressManager:
    """Manages progress tracking for parsing tasks"""

    def __init__(self, data_folder: str):
        """
        Initialize ProgressManager.

        Args:
            data_folder: Path to store progress data
        """
        self.data_folder = data_folder
        self.progress_file = os.path.join(data_folder, 'progress_state.json')
        self._lock = threading.RLock()
        self._states: Dict[str, ProgressState] = {}

        # Ensure data folder exists
        os.makedirs(data_folder, exist_ok=True)

        # Load existing states
        self._load_states()

        # Start cleanup thread for old tasks
        self._start_cleanup_thread()

    def _load_states(self) -> None:
        """Load progress states from file"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                with self._lock:
                    self._states.clear()
                    for task_id, state_data in data.items():
                        try:
                            self._states[task_id] = ProgressState.from_dict(state_data)
                        except (KeyError, ValueError) as e:
                            logger.warning(f"Failed to load progress state for {task_id}: {e}")

                logger.info(f"Loaded {len(self._states)} progress states from {self.progress_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load progress states: {e}")
                self._states = {}
        else:
            self._states = {}

    def _save_states(self) -> None:
        """Save progress states to file"""
        try:
            with self._lock:
                data = {task_id: state.to_dict() for task_id, state in self._states.items()}

            # Create temp file first to avoid corruption
            temp_file = self.progress_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

            # Atomic rename
            os.replace(temp_file, self.progress_file)

        except IOError as e:
            logger.error(f"Failed to save progress states: {e}")

    def _start_cleanup_thread(self) -> None:
        """Start background thread to clean up old tasks"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(3600)  # Run every hour
                    self.cleanup_old_tasks(max_age_hours=24)
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")

        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()

    def create_task(self, filename: str, task_type: TaskType,
                    total_steps: int = 100, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new progress tracking task.

        Args:
            filename: Name of the file being processed
            task_type: Type of task
            total_steps: Total number of steps for progress calculation
            metadata: Additional metadata for the task

        Returns:
            Task ID for tracking progress
        """
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        state = ProgressState(
            task_id=task_id,
            filename=filename,
            task_type=task_type,
            status=TaskStatus.PENDING,
            progress=0.0,
            total_steps=total_steps,
            current_step=0,
            step_description="Waiting to start",
            message=f"{task_type.value.capitalize()} task created for {filename}",
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
            result=None,
            error=None
        )

        with self._lock:
            self._states[task_id] = state

        self._save_states()
        logger.info(f"Created progress task {task_id} for {filename} ({task_type.value})")

        return task_id

    def update_progress(self, task_id: str, current_step: int, step_description: str,
                        message: Optional[str] = None, metadata_updates: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update progress for a task.

        Args:
            task_id: ID of the task to update
            current_step: Current step number (0 to total_steps)
            step_description: Description of current step
            message: Optional progress message
            metadata_updates: Optional metadata updates

        Returns:
            True if successful, False if task not found
        """
        with self._lock:
            if task_id not in self._states:
                logger.warning(f"Task {task_id} not found for progress update")
                return False

            state = self._states[task_id]

            # Calculate progress
            if state.total_steps > 0:
                progress = min(current_step / state.total_steps, 1.0)
            else:
                progress = 0.0

            # Update state
            state.status = TaskStatus.RUNNING
            state.current_step = current_step
            state.step_description = step_description
            state.progress = progress
            state.updated_at = datetime.now().isoformat()

            if message:
                state.message = message

            if metadata_updates:
                state.metadata.update(metadata_updates)

        self._save_states()
        logger.debug(f"Updated progress for task {task_id}: step {current_step}/{state.total_steps} ({progress:.1%})")

        return True

    def complete_task(self, task_id: str, result: Dict[str, Any], message: Optional[str] = None) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: ID of the task to complete
            result: Task result data
            message: Optional completion message

        Returns:
            True if successful, False if task not found
        """
        with self._lock:
            if task_id not in self._states:
                logger.warning(f"Task {task_id} not found for completion")
                return False

            state = self._states[task_id]
            state.status = TaskStatus.COMPLETED
            state.progress = 1.0
            state.current_step = state.total_steps
            state.step_description = "Completed"
            state.result = result
            state.updated_at = datetime.now().isoformat()

            if message:
                state.message = message
            else:
                state.message = f"Task completed successfully"

        self._save_states()
        logger.info(f"Completed task {task_id} with result: {result}")

        return True

    def fail_task(self, task_id: str, error: str, message: Optional[str] = None) -> bool:
        """
        Mark a task as failed.

        Args:
            task_id: ID of the task to mark as failed
            error: Error message or description
            message: Optional failure message

        Returns:
            True if successful, False if task not found
        """
        with self._lock:
            if task_id not in self._states:
                logger.warning(f"Task {task_id} not found for failure")
                return False

            state = self._states[task_id]
            state.status = TaskStatus.FAILED
            state.error = error
            state.updated_at = datetime.now().isoformat()

            if message:
                state.message = message
            else:
                state.message = f"Task failed: {error}"

        self._save_states()
        logger.error(f"Task {task_id} failed: {error}")

        return True

    def cancel_task(self, task_id: str, message: Optional[str] = None) -> bool:
        """
        Cancel a task.

        Args:
            task_id: ID of the task to cancel
            message: Optional cancellation message

        Returns:
            True if successful, False if task not found
        """
        with self._lock:
            if task_id not in self._states:
                logger.warning(f"Task {task_id} not found for cancellation")
                return False

            state = self._states[task_id]
            state.status = TaskStatus.CANCELLED
            state.updated_at = datetime.now().isoformat()

            if message:
                state.message = message
            else:
                state.message = "Task cancelled by user"

        self._save_states()
        logger.info(f"Cancelled task {task_id}")

        return True

    def get_task_state(self, task_id: str) -> Optional[ProgressState]:
        """
        Get current state of a task.

        Args:
            task_id: ID of the task

        Returns:
            ProgressState if found, None otherwise
        """
        with self._lock:
            return self._states.get(task_id)

    def get_all_tasks(self, include_completed: bool = True, include_failed: bool = True) -> List[ProgressState]:
        """
        Get all tasks.

        Args:
            include_completed: Whether to include completed tasks
            include_failed: Whether to include failed tasks

        Returns:
            List of ProgressState objects
        """
        with self._lock:
            tasks = list(self._states.values())

        if not include_completed:
            tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]

        if not include_failed:
            tasks = [t for t in tasks if t.status != TaskStatus.FAILED]

        # Sort by updated_at (most recent first)
        tasks.sort(key=lambda t: t.updated_at, reverse=True)

        return tasks

    def get_tasks_by_filename(self, filename: str) -> List[ProgressState]:
        """
        Get all tasks for a specific filename.

        Args:
            filename: Name of the file

        Returns:
            List of ProgressState objects for the file
        """
        with self._lock:
            tasks = [state for state in self._states.values() if state.filename == filename]

        # Sort by updated_at (most recent first)
        tasks.sort(key=lambda t: t.updated_at, reverse=True)

        return tasks

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: ID of the task to delete

        Returns:
            True if successful, False if task not found
        """
        with self._lock:
            if task_id not in self._states:
                return False

            del self._states[task_id]

        self._save_states()
        logger.info(f"Deleted task {task_id}")

        return True

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed/cancelled tasks.

        Args:
            max_age_hours: Maximum age in hours to keep tasks

        Returns:
            Number of tasks cleaned up
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cutoff_iso = cutoff_time.isoformat()

        tasks_to_delete = []

        with self._lock:
            for task_id, state in self._states.items():
                # Only clean up completed, failed, or cancelled tasks
                if state.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    if state.updated_at < cutoff_iso:
                        tasks_to_delete.append(task_id)

        for task_id in tasks_to_delete:
            with self._lock:
                del self._states[task_id]

        if tasks_to_delete:
            self._save_states()
            logger.info(f"Cleaned up {len(tasks_to_delete)} old tasks")

        return len(tasks_to_delete)

    def get_task_stats(self) -> Dict[str, Any]:
        """
        Get statistics about tasks.

        Returns:
            Dictionary with task statistics
        """
        with self._lock:
            total = len(self._states)

            status_counts = {}
            for state in self._states.values():
                status = state.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            type_counts = {}
            for state in self._states.values():
                task_type = state.task_type.value
                type_counts[task_type] = type_counts.get(task_type, 0) + 1

        return {
            'total_tasks': total,
            'status_counts': status_counts,
            'type_counts': type_counts,
            'timestamp': datetime.now().isoformat()
        }