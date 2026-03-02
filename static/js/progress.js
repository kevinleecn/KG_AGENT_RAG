/**
 * Progress tracking for document parsing
 */

// Helper function to escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

class ProgressTracker {
    // Configuration constants
    static DEFAULT_POLLING_INTERVAL = 2000; // 2 seconds
    static MAX_POLLING_ATTEMPTS = 300; // 10 minutes at 2s intervals

    constructor() {
        this.activeTasks = new Map(); // task_id -> {filename, pollingInterval}
        this.updateCallbacks = new Set();
        this.pollingInterval = ProgressTracker.DEFAULT_POLLING_INTERVAL;
        this.maxPollingAttempts = ProgressTracker.MAX_POLLING_ATTEMPTS;
    }

    /**
     * Start tracking a parsing task
     * @param {string} taskId - Task ID to track
     * @param {string} filename - Name of the file being parsed
     * @param {Function} onUpdate - Callback when progress updates
     * @param {Function} onComplete - Callback when task completes
     * @param {Function} onError - Callback when task fails
     */
    startTracking(taskId, filename, onUpdate = null, onComplete = null, onError = null) {
        console.log(`Starting progress tracking for task ${taskId} (${filename})`);

        if (this.activeTasks.has(taskId)) {
            console.warn(`Task ${taskId} is already being tracked`);
            return;
        }

        const taskInfo = {
            taskId,
            filename,
            onUpdate,
            onComplete,
            onError,
            pollingAttempts: 0,
            lastProgress: null,
            pollingInterval: null
        };

        this.activeTasks.set(taskId, taskInfo);

        // Start polling immediately
        this._pollTaskProgress(taskId);

        // Set up periodic polling
        taskInfo.pollingInterval = setInterval(() => {
            this._pollTaskProgress(taskId);
        }, this.pollingInterval);

        return taskId;
    }

    /**
     * Stop tracking a task
     * @param {string} taskId - Task ID to stop tracking
     */
    stopTracking(taskId) {
        const taskInfo = this.activeTasks.get(taskId);
        if (!taskInfo) {
            return;
        }

        if (taskInfo.pollingInterval) {
            clearInterval(taskInfo.pollingInterval);
        }

        this.activeTasks.delete(taskId);
        console.log(`Stopped tracking task ${taskId}`);
    }

    /**
     * Stop tracking all tasks
     */
    stopAllTracking() {
        for (const taskId of this.activeTasks.keys()) {
            this.stopTracking(taskId);
        }
    }

    /**
     * Get task info for a filename
     * @param {string} filename - Filename to get tasks for
     * @returns {Array} Array of task info objects
     */
    getTasksForFile(filename) {
        const tasks = [];
        for (const taskInfo of this.activeTasks.values()) {
            if (taskInfo.filename === filename) {
                tasks.push({
                    taskId: taskInfo.taskId,
                    filename: taskInfo.filename,
                    lastProgress: taskInfo.lastProgress
                });
            }
        }
        return tasks;
    }

    /**
     * Check if a file has active parsing tasks
     * @param {string} filename - Filename to check
     * @returns {boolean} True if file has active tasks
     */
    hasActiveTasks(filename) {
        for (const taskInfo of this.activeTasks.values()) {
            if (taskInfo.filename === filename &&
                taskInfo.lastProgress &&
                taskInfo.lastProgress.status !== 'completed' &&
                taskInfo.lastProgress.status !== 'failed' &&
                taskInfo.lastProgress.status !== 'cancelled') {
                return true;
            }
        }
        return false;
    }

    /**
     * Poll task progress from server
     * @param {string} taskId - Task ID to poll
     * @private
     */
    _pollTaskProgress(taskId) {
        const taskInfo = this.activeTasks.get(taskId);
        if (!taskInfo) {
            return;
        }

        taskInfo.pollingAttempts++;

        // Stop polling if we've exceeded max attempts
        if (taskInfo.pollingAttempts > this.maxPollingAttempts) {
            console.warn(`Max polling attempts reached for task ${taskId}`);
            this.stopTracking(taskId);
            if (taskInfo.onError) {
                taskInfo.onError({
                    taskId,
                    filename: taskInfo.filename,
                    error: 'Polling timeout - task may still be running'
                });
            }
            return;
        }

        fetch(`/progress/${taskId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (!data.success) {
                    throw new Error(data.error || 'Unknown error');
                }

                const progress = data.progress;
                console.log(`Progress received for task ${taskId}:`, progress);
                console.log(`Status: ${progress.status}, Progress: ${progress.progress}`);
                taskInfo.lastProgress = progress;
                // Reset polling attempts counter on successful response
                taskInfo.pollingAttempts = 0;

                // Notify update callback
                if (taskInfo.onUpdate) {
                    console.log(`Calling onUpdate callback for task ${taskId}`);
                    taskInfo.onUpdate(progress);
                }

                // Notify global callbacks
                this._notifyUpdateCallbacks(progress);

                // Handle task completion
                if (progress.status === 'completed') {
                    console.log(`Task ${taskId} completed successfully`);
                    this.stopTracking(taskId);
                    if (taskInfo.onComplete) {
                        taskInfo.onComplete(progress);
                    }
                }
                // Handle task failure
                else if (progress.status === 'failed') {
                    console.error(`Task ${taskId} failed: ${progress.error}`);
                    this.stopTracking(taskId);
                    if (taskInfo.onError) {
                        taskInfo.onError(progress);
                    }
                }
                // Handle task cancellation
                else if (progress.status === 'cancelled') {
                    console.log(`Task ${taskId} was cancelled`);
                    this.stopTracking(taskId);
                    if (taskInfo.onError) {
                        taskInfo.onError(progress);
                    }
                }
            })
            .catch(error => {
                console.error(`Error polling progress for task ${taskId}:`, error);

                // Only stop tracking on persistent errors
                if (taskInfo.pollingAttempts > this.maxPollingAttempts) {
                    console.warn(`Stopping tracking for task ${taskId} due to persistent errors`);
                    this.stopTracking(taskId);
                    if (taskInfo.onError) {
                        taskInfo.onError({
                            taskId,
                            filename: taskInfo.filename,
                            error: `Failed to get progress: ${error.message}`
                        });
                    }
                }
            });
    }

    /**
     * Cancel a parsing task
     * @param {string} taskId - Task ID to cancel
     * @returns {Promise} Promise that resolves when cancellation is complete
     */
    cancelTask(taskId) {
        return fetch(`/progress/cancel/${taskId}`, {
            method: 'POST'
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log(`Task ${taskId} cancellation requested`);
                    this.stopTracking(taskId);
                } else {
                    throw new Error(data.error || 'Failed to cancel task');
                }
                return data;
            });
    }

    /**
     * Get all tasks for a file from server
     * @param {string} filename - Filename to get tasks for
     * @returns {Promise} Promise that resolves with task list
     */
    getFileTasks(filename) {
        return fetch(`/progress/file/${filename}`)
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    throw new Error(data.error || 'Failed to get file tasks');
                }
                return data.tasks;
            });
    }

    /**
     * Get all active tasks from server
     * @returns {Promise} Promise that resolves with all tasks
     */
    getAllTasks() {
        return fetch('/progress/all')
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    throw new Error(data.error || 'Failed to get all tasks');
                }
                return data.tasks;
            });
    }

    /**
     * Register a callback for progress updates on any task
     * @param {Function} callback - Callback function
     */
    onAnyUpdate(callback) {
        this.updateCallbacks.add(callback);
    }

    /**
     * Unregister a callback
     * @param {Function} callback - Callback function to remove
     */
    offAnyUpdate(callback) {
        this.updateCallbacks.delete(callback);
    }

    /**
     * Notify all update callbacks
     * @param {Object} progress - Progress data
     * @private
     */
    _notifyUpdateCallbacks(progress) {
        for (const callback of this.updateCallbacks) {
            try {
                callback(progress);
            } catch (error) {
                console.error('Error in progress update callback:', error);
            }
        }
    }

    /**
     * Create a progress bar HTML element
     * @param {Object} progress - Progress data
     * @returns {string} HTML string for progress bar
     */
    static createProgressBar(progress) {
        const percent = Math.round(progress.progress * 100);
        let statusClass = '';
        let statusText = progress.status;

        switch (progress.status) {
            case 'pending':
                statusClass = 'bg-secondary';
                statusText = '等待中';
                break;
            case 'running':
                statusClass = 'bg-info progress-bar-striped progress-bar-animated';
                statusText = '处理中';
                break;
            case 'completed':
                statusClass = 'bg-success';
                statusText = '已完成';
                break;
            case 'failed':
                statusClass = 'bg-danger';
                statusText = '失败';
                break;
            case 'cancelled':
                statusClass = 'bg-warning';
                statusText = '已取消';
                break;
        }

        // Escape user-provided text fields
        const stepDesc = progress.step_description ? escapeHtml(progress.step_description) : '';
        const message = progress.message ? escapeHtml(progress.message) : '';

        return `
            <div class="progress mt-1" style="height: 20px;">
                <div class="progress-bar ${statusClass}"
                     role="progressbar"
                     style="width: ${percent}%;"
                     aria-valuenow="${percent}"
                     aria-valuemin="0"
                     aria-valuemax="100">
                    ${percent}% - ${statusText}
                </div>
            </div>
            ${stepDesc ? `<small class="text-muted">${stepDesc}</small>` : ''}
            ${message ? `<div class="small text-muted mt-1">${message}</div>` : ''}
        `;
    }

    /**
     * Create a progress status badge
     * @param {Object} progress - Progress data
     * @returns {string} HTML string for badge
     */
    static createProgressBadge(progress) {
        let badgeClass = '';
        let badgeText = progress.status;

        switch (progress.status) {
            case 'pending':
                badgeClass = 'bg-secondary';
                badgeText = '等待中';
                break;
            case 'running':
                badgeClass = 'bg-info';
                badgeText = '处理中';
                break;
            case 'completed':
                badgeClass = 'bg-success';
                badgeText = '已完成';
                break;
            case 'failed':
                badgeClass = 'bg-danger';
                badgeText = '失败';
                break;
            case 'cancelled':
                badgeClass = 'bg-warning';
                badgeText = '已取消';
                break;
        }

        return `<span class="badge ${badgeClass}">${badgeText}</span>`;
    }

    /**
     * Create detailed progress report
     * @param {Object} progress - Progress data
     * @returns {string} HTML string for progress report
     */
    static createProgressReport(progress) {
        const percent = Math.round(progress.progress * 100);
        const created = new Date(progress.created_at).toLocaleString();
        const updated = new Date(progress.updated_at).toLocaleString();
        // Escape date strings for safe HTML insertion
        const escapedCreated = escapeHtml(created);
        const escapedUpdated = escapeHtml(updated);

        let resultHtml = '';
        if (progress.result) {
            // Escape JSON string for safe HTML insertion
            const resultJson = JSON.stringify(progress.result, null, 2);
            resultHtml = `
                <div class="mt-2">
                    <h6>Result:</h6>
                    <pre class="bg-light p-2 small">${escapeHtml(resultJson)}</pre>
                </div>
            `;
        }

        let errorHtml = '';
        if (progress.error) {
            // Escape error message for safe HTML insertion
            const escapedError = escapeHtml(progress.error);
            errorHtml = `
                <div class="mt-2">
                    <h6 class="text-danger">Error:</h6>
                    <div class="alert alert-danger small">${escapedError}</div>
                </div>
            `;
        }

        // Escape text fields from progress data
        const stepDesc = progress.step_description ? escapeHtml(progress.step_description) : 'N/A';
        const message = progress.message ? escapeHtml(progress.message) : 'N/A';
        const taskType = progress.task_type ? escapeHtml(progress.task_type) : 'N/A';

        return `
            <div class="card mt-2">
                <div class="card-header">
                    <h6 class="mb-0">解析进度报告</h6>
                </div>
                <div class="card-body">
                    <dl class="row mb-0">
                        <dt class="col-sm-3">状态</dt>
                        <dd class="col-sm-9">${ProgressTracker.createProgressBadge(progress)}</dd>

                        <dt class="col-sm-3">进度</dt>
                        <dd class="col-sm-9">${percent}%</dd>

                        <dt class="col-sm-3">当前步骤</dt>
                        <dd class="col-sm-9">${stepDesc}</dd>

                        <dt class="col-sm-3">消息</dt>
                        <dd class="col-sm-9">${message}</dd>

                        <dt class="col-sm-3">任务创建时间</dt>
                        <dd class="col-sm-9">${escapedCreated}</dd>

                        <dt class="col-sm-3">最后更新</dt>
                        <dd class="col-sm-9">${escapedUpdated}</dd>

                        <dt class="col-sm-3">任务类型</dt>
                        <dd class="col-sm-9">${taskType}</dd>
                    </dl>
                    ${resultHtml}
                    ${errorHtml}
                </div>
            </div>
        `;
    }

    /**
     * Resume tracking for any active tasks
     * This method is called on page load to resume tracking for any tasks
     * that were active before page refresh
     */
    resumeTracking() {
        console.log('Resuming tracking for active tasks');
        // This method is intentionally left empty as active tasks
        // are already tracked in memory. It exists for compatibility
        // with the initialization code.
    }
}


/**
 * Update UI for a file's progress
 * @param {string} filename - Filename to update
 * @param {Object} progress - Progress data
 */
function updateFileProgressUI(filename, progress) {
    // Try to find uploaded file list item (list group item)
    const fileListItem = document.querySelector(`.uploaded-file-item[data-filename="${filename}"]`);

    if (fileListItem) {
        // Update list group item UI
        updateListGroupItemProgressUI(fileListItem, progress);
        return;
    }

    // Fall back to table row (for backward compatibility)
    const fileRow = document.querySelector(`tr[data-filename="${filename}"]`);
    if (!fileRow) {
        return;
    }

    // Update progress cell
    const progressCell = fileRow.querySelector('.file-progress');
    if (progressCell) {
        progressCell.innerHTML = ProgressTracker.createProgressBar(progress);
    }

    // Update status badge
    const statusCell = fileRow.querySelector('.file-status');
    if (statusCell) {
        statusCell.innerHTML = ProgressTracker.createProgressBadge(progress);
    }

    // Update actions cell with cancel button if running
    const actionsCell = fileRow.querySelector('.file-actions');
    if (actionsCell && progress.status === 'running') {
        // Add cancel button if not already present
        if (!actionsCell.querySelector('.cancel-parsing-btn')) {
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn btn-sm btn-outline-danger cancel-parsing-btn';
            cancelBtn.innerHTML = '<i class="fas fa-times me-1"></i>Cancel';
            cancelBtn.onclick = function() {
                cancelParsing(progress.task_id, filename);
            };
            actionsCell.appendChild(cancelBtn);
        }
    } else if (actionsCell && progress.status !== 'running') {
        // Remove cancel button if present
        const cancelBtn = actionsCell.querySelector('.cancel-parsing-btn');
        if (cancelBtn) {
            cancelBtn.remove();
        }
    }
}

/**
 * Update progress UI for a list group item
 * @param {HTMLElement} fileListItem - .uploaded-file-item element
 * @param {Object} progress - Progress data
 */
function updateListGroupItemProgressUI(fileListItem, progress) {
    const $fileItem = $(fileListItem);
    const progressContainer = fileListItem.querySelector('.file-progress-container');
    const resultContainer = fileListItem.querySelector('.file-result-container');

    if (!progressContainer) {
        // If no progress container exists, create one
        const actionsDiv = fileListItem.querySelector('.file-actions');
        if (actionsDiv) {
            const newProgressContainer = document.createElement('div');
            newProgressContainer.className = 'file-progress-container mt-2';
            actionsDiv.parentNode.insertBefore(newProgressContainer, actionsDiv.nextSibling);
        } else {
            return; // Cannot find where to insert progress container
        }
    }

    // Hide result container if visible
    if (resultContainer) {
        resultContainer.classList.add('d-none');
        resultContainer.innerHTML = '';
    }

    // Show progress container
    progressContainer.classList.remove('d-none');

    // Create progress bar HTML
    const progressBarHtml = ProgressTracker.createProgressBar(progress);

    // Add cancel button if task is running
    let actionHtml = '';
    if (progress.status === 'running') {
        // Escape task ID for safe HTML insertion
        const escapedTaskId = escapeHtml(progress.task_id);
        actionHtml = `
            <div class="mt-2">
                <button class="btn btn-sm btn-outline-danger cancel-parsing-btn"
                        data-task-id="${escapedTaskId}">
                    <i class="fas fa-times me-1"></i>Cancel
                </button>
            </div>
        `;
    }

    progressContainer.innerHTML = progressBarHtml + actionHtml;

    // Update data attribute for status
    $fileItem.data('parsing-status', progress.status);

    // If task is completed, update UI accordingly
    if (progress.status === 'completed') {
        // Hide progress container
        progressContainer.classList.add('d-none');
        progressContainer.innerHTML = '';

        // Update parsed status
        $fileItem.data('parsed', true);

        // Add Parsed badge if not already present
        const fileNameDiv = fileListItem.querySelector('.file-name');
        if (fileNameDiv && !fileNameDiv.querySelector('.badge.bg-success')) {
            const badge = document.createElement('span');
            badge.className = 'badge bg-success ms-2';
            badge.textContent = '已解析';
            fileNameDiv.appendChild(badge);
        }

        // Show result container if available
        if (resultContainer) {
            resultContainer.classList.remove('d-none');
            // Create simple result report
            const result = progress.result || {};
            const entityCount = result.entity_count || 0;
            const relationCount = result.relationship_count || 0;
            const textLength = result.text_length || 0;
            const wordCount = result.word_count || 0;
            // Escape values for safe HTML insertion
            const escapedEntityCount = escapeHtml(String(entityCount));
            const escapedRelationCount = escapeHtml(String(relationCount));
            const escapedTextLength = escapeHtml(String(textLength));
            const escapedWordCount = escapeHtml(String(wordCount));

            let reportHtml = `
                <div class="parsing-result-summary">
                    <div class="d-flex align-items-center">
                        <span class="badge bg-success me-2">
                            <i class="fas fa-check-circle me-1"></i>已解析
                        </span>
                        <span class="small text-muted">
            `;

            if (entityCount > 0 || relationCount > 0) {
                reportHtml += `${escapedEntityCount} 个实体 · ${escapedRelationCount} 个关系`;
            } else {
                reportHtml += `${escapedTextLength} 字符 · ${escapedWordCount} 词`;
            }

            reportHtml += `
                        </span>
                    </div>
                </div>
            `;

            resultContainer.innerHTML = reportHtml;
        }

        // Remove parse button if present
        const parseBtn = fileListItem.querySelector('.parse-file-btn');
        if (parseBtn) {
            parseBtn.remove();
        }
    }
    // If task failed or cancelled, show error
    else if (progress.status === 'failed' || progress.status === 'cancelled') {
        // Hide progress container
        progressContainer.classList.add('d-none');
        progressContainer.innerHTML = '';

        // Show error in result container
        if (resultContainer) {
            resultContainer.classList.remove('d-none');
            const errorMessage = progress.error || '解析失败';
            // Clear result container
            resultContainer.innerHTML = '';

            // Create alert element safely
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger alert-sm mb-0';

            // Add icon
            const icon = document.createElement('i');
            icon.className = 'fas fa-exclamation-triangle me-2';
            alertDiv.appendChild(icon);

            // Add error message as text node (escaped)
            const errorText = document.createTextNode(errorMessage);
            alertDiv.appendChild(errorText);

            resultContainer.appendChild(alertDiv);
        }

        // Restore parse button if not present
        const fileActions = fileListItem.querySelector('.file-actions');
        if (fileActions && !fileActions.querySelector('.parse-file-btn')) {
            const parseBtn = document.createElement('button');
            parseBtn.className = 'btn btn-sm btn-outline-warning parse-file-btn';
            parseBtn.title = '解析文档以提取知识';
            parseBtn.innerHTML = '<i class="fas fa-cogs"></i>';
            parseBtn.onclick = function(e) {
                e.stopPropagation();
            };
            fileActions.insertBefore(parseBtn, fileActions.firstChild);
        }
    }
}

/**
 * Cancel parsing for a task
 * @param {string} taskId - Task ID to cancel
 * @param {string} filename - Filename for UI updates
 */
function cancelParsing(taskId, filename) {
    if (!confirm('Are you sure you want to cancel this parsing task?')) {
        return;
    }

    window.progressTracker.cancelTask(taskId)
        .then(() => {
            showAlert('Parsing cancelled successfully', 'success');
            // UI will update via progress polling
        })
        .catch(error => {
            console.error('Failed to cancel parsing:', error);
            showAlert(`Failed to cancel parsing: ${error.message}`, 'danger');
        });
}

/**
 * Show alert message
 * @param {string} message - Alert message
 * @param {string} type - Alert type (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    // Implementation depends on existing UI
    // This is a placeholder - should be integrated with existing alert system
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const container = document.querySelector('.alerts-container') || document.body;
    container.prepend(alertDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Make ProgressTracker class globally available
window.ProgressTracker = ProgressTracker;

// Initialize progress tracker immediately
try {
    window.progressTracker = new ProgressTracker();
    console.log('ProgressTracker instance created successfully');
} catch (error) {
    console.error('Failed to create ProgressTracker instance:', error);
    window.progressTracker = null;
}

// Resume tracking any active tasks when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('DOM loaded, resuming tracking');
        if (window.progressTracker && window.progressTracker.resumeTracking) {
            window.progressTracker.resumeTracking();
        } else {
            console.error('Progress tracker not available for resumeTracking');
        }
    });
} else {
    // DOM already loaded
    console.log('DOM already loaded, resuming tracking');
    if (window.progressTracker && window.progressTracker.resumeTracking) {
        window.progressTracker.resumeTracking();
    } else {
        console.error('Progress tracker not available for resumeTracking');
    }
}