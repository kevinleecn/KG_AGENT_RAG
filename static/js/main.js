/**
 * Knowledge Graph QA Demo - Main JavaScript
 * Phase 1: File Upload Functionality
 */

$(document).ready(function() {
    // DOM Elements
    const $fileInput = $('#fileInput');
    const $browseBtn = $('#browseBtn');
    const $dropZone = $('#dropZone');
    const $fileListContainer = $('#fileListContainer');
    const $fileList = $('#fileList');
    const $uploadBtn = $('#uploadBtn');
    const $resultsContainer = $('#resultsContainer');
    const $refreshFilesBtn = $('#refreshFilesBtn');
    const $filesLoading = $('#filesLoading');
    const $filesEmpty = $('#filesEmpty');
    const $filesListContainer = $('#filesListContainer');
    const $uploadedFilesList = $('#uploadedFilesList');
    const $filesCount = $('#filesCount');
    const $totalSize = $('#totalSize');
    const $extractionMethodSelect = $('#extractionMethodSelect');

    // File tracking
    let selectedFiles = [];
    let currentDocument = null;
    let currentExtractionMethod = 'spacy'; // Default extraction method

    // Initialize
    console.log('Main.js initialized. Checking progress tracker:', window.progressTracker);
    if (!window.progressTracker) {
        console.error('Progress tracker not available in main.js initialization');
    } else {
        console.log('Progress tracker available:', typeof window.progressTracker.startTracking);
    }

    // Load saved extraction method from localStorage
    const savedMethod = localStorage.getItem('extractionMethod');
    if (savedMethod && ['spacy', 'llm'].includes(savedMethod)) {
        currentExtractionMethod = savedMethod;
        $extractionMethodSelect.val(savedMethod);
    }

    // Handle extraction method change
    $extractionMethodSelect.on('change', function() {
        currentExtractionMethod = $(this).val();
        localStorage.setItem('extractionMethod', currentExtractionMethod);
        console.log('Extraction method changed to:', currentExtractionMethod);
    });

    initFileUpload();
    initFileList();

    /**
     * Initialize file upload functionality
     */
    function initFileUpload() {
        // Browse button click
        $browseBtn.on('click', function() {
            $fileInput.click();
        });

        // File input change
        $fileInput.on('change', handleFileSelect);

        // Drag and drop events
        $dropZone.on('dragover', handleDragOver);
        $dropZone.on('dragleave', handleDragLeave);
        $dropZone.on('drop', handleFileDrop);

        // Upload button click
        $uploadBtn.on('click', uploadFiles);
    }

    /**
     * Initialize file list functionality
     */
    function initFileList() {
        // Load files on page load
        loadUploadedFiles();

        // Refresh button click
        $refreshFilesBtn.on('click', function() {
            loadUploadedFiles();
            showAlert('info', '文件列表已刷新。');
        });
    }

    /**
     * Handle file selection from input
     */
    function handleFileSelect(e) {
        const files = Array.from(e.target.files);
        addFiles(files);
        $fileInput.val(''); // Reset input
    }

    /**
     * Handle drag over event
     */
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        $dropZone.addClass('drag-over');
    }

    /**
     * Handle drag leave event
     */
    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        $dropZone.removeClass('drag-over');
    }

    /**
     * Handle file drop event
     */
    function handleFileDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        $dropZone.removeClass('drag-over');

        const files = Array.from(e.originalEvent.dataTransfer.files);
        addFiles(files);
    }

    /**
     * Add files to selection
     */
    function addFiles(files) {
        const validFiles = files.filter(file => {
            const ext = '.' + file.name.split('.').pop().toLowerCase();
            const allowed = ['.txt', '.docx', '.pdf', '.pptx'];
            return allowed.includes(ext);
        });

        if (validFiles.length === 0) {
            showAlert('warning', '未选择有效文件。请选择 .txt、.docx、.pdf 或 .pptx 文件。');
            return;
        }

        // Add to selected files
        validFiles.forEach(file => {
            if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                selectedFiles.push(file);
            }
        });

        updateFileList();
    }

    /**
     * Update file list UI
     */
    function updateFileList() {
        if (selectedFiles.length === 0) {
            $fileListContainer.hide();
            $uploadBtn.prop('disabled', true);
            return;
        }

        $fileListContainer.show();
        $uploadBtn.prop('disabled', false);
        $fileList.empty();

        selectedFiles.forEach((file, index) => {
            const fileItem = createFileListItem(file, index);
            $fileList.append(fileItem);
        });
    }

    /**
     * Create file list item HTML
     */
    function createFileListItem(file, index) {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        const fileSize = formatFileSize(file.size);
        const fileIcon = getFileIcon(ext);

        return `
            <div class="list-group-item file-list-item" data-index="${index}">
                <div class="file-info">
                    <div class="file-icon ${ext.substring(1)}-file">
                        <i class="${fileIcon}"></i>
                    </div>
                    <div class="file-details">
                        <div class="file-name">${escapeHtml(file.name)}</div>
                        <div class="file-size">${fileSize}</div>
                    </div>
                </div>
                <div class="file-actions">
                    <button type="button" class="btn btn-sm btn-outline-danger remove-file" data-index="${index}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Upload files to server
     */
    function uploadFiles() {
        if (selectedFiles.length === 0) {
            showAlert('warning', '未选择文件。');
            return;
        }

        // Disable upload button and show loading state
        $uploadBtn.prop('disabled', true);
        $uploadBtn.html('<i class="fas fa-spinner fa-spin me-2"></i>正在上传...');

        // Create FormData
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        // Update UI to show uploading state
        $('.file-list-item').addClass('uploading');

        // Send AJAX request
        $.ajax({
            url: '/upload',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: handleUploadSuccess,
            error: handleUploadError,
            complete: function() {
                $uploadBtn.html('<i class="fas fa-upload me-2"></i>上传文件');
                $('.file-list-item').removeClass('uploading');
            }
        });
    }

    /**
     * Handle upload success response
     */
    function handleUploadSuccess(response) {
        if (response.success) {
            // Show success message
            showAlert('success', response.message);

            // Update file list items with success state
            response.uploaded.forEach(uploadedFile => {
                const index = selectedFiles.findIndex(f => f.name === uploadedFile.filename);
                if (index !== -1) {
                    $(`.file-list-item[data-index="${index}"]`).addClass('success');
                }
            });

            // Clear selected files after successful upload
            selectedFiles = [];
            updateFileList();

            // Show results
            showUploadResults(response);

            // Refresh uploaded files list
            loadUploadedFiles();
        } else {
            showAlert('danger', response.error || '上传失败。');
        }
    }

    /**
     * Handle upload error
     */
    function handleUploadError(xhr) {
        let errorMessage = '上传失败，请重试。';

        try {
            const response = JSON.parse(xhr.responseText);
            errorMessage = response.error || errorMessage;
        } catch (e) {
            // Use default error message
        }

        showAlert('danger', errorMessage);
    }

    /**
     * Show upload results
     */
    function showUploadResults(response) {
        $resultsContainer.show().empty();

        let html = `
            <div class="card">
                <div class="card-header bg-success text-white">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-check-circle me-2"></i>Upload Complete
                    </h5>
                </div>
                <div class="card-body">
        `;

        if (response.uploaded && response.uploaded.length > 0) {
            html += `
                <h6>Uploaded Files (${response.uploaded.length})</h6>
                <ul class="list-group mb-3">
            `;

            response.uploaded.forEach(file => {
                html += `
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        <div>
                            <i class="${getFileIcon('.' + file.filename.split('.').pop())} me-2"></i>
                            ${escapeHtml(file.filename)}
                        </div>
                        <span class="badge bg-light text-dark">${formatFileSize(file.size)}</span>
                    </li>
                `;
            });

            html += `</ul>`;
        }

        if (response.skipped && response.skipped.length > 0) {
            html += `
                <h6 class="text-warning">Skipped Files (${response.skipped.length})</h6>
                <p class="small text-muted">These files were not uploaded due to invalid format.</p>
                <ul class="list-group">
            `;

            response.skipped.forEach(filename => {
                html += `
                    <li class="list-group-item">
                        <i class="fas fa-exclamation-triangle text-warning me-2"></i>
                        ${escapeHtml(filename)}
                    </li>
                `;
            });

            html += `</ul>`;
        }

        html += `
                </div>
                <div class="card-footer">
                    <button type="button" class="btn btn-outline-primary" id="uploadMoreBtn">
                        <i class="fas fa-plus me-2"></i>Upload More Files
                    </button>
                </div>
            </div>
        `;

        $resultsContainer.html(html);

        // Add event listener for upload more button
        $('#uploadMoreBtn').on('click', function() {
            $resultsContainer.hide();
        });
    }

    /**
     * Show alert message
     */
    function showAlert(type, message) {
        // Remove existing alerts
        $('.alert').remove();

        // Create new alert
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        // Insert after main container
        $('main .container').prepend(alertHtml);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            $(`.alert-${type}`).alert('close');
        }, 5000);
    }

    /**
     * Get file icon based on extension
     */
    function getFileIcon(ext) {
        switch (ext) {
            case '.txt': return 'fas fa-file-alt';
            case '.docx': return 'fas fa-file-word';
            case '.pdf': return 'fas fa-file-pdf';
            case '.pptx': return 'fas fa-file-powerpoint';
            default: return 'fas fa-file';
        }
    }

    /**
     * Format file size in human readable format
     */
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Load uploaded files from server
     */
    function loadUploadedFiles() {
        // Show loading state
        $filesLoading.show();
        $filesEmpty.hide();
        $filesListContainer.hide();

        $.ajax({
            url: '/files',
            type: 'GET',
            success: function(response) {
                if (response.success) {
                    renderUploadedFilesList(response);
                } else {
                    showAlert('danger', '加载文件列表失败：' + (response.error || '未知错误'));
                    showEmptyState();
                }
            },
            error: function(xhr) {
                let errorMessage = '加载文件列表失败，请重试。';
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMessage = response.error || errorMessage;
                } catch (e) {
                    // Use default error message
                }
                showAlert('danger', errorMessage);
                showEmptyState();
            },
            complete: function() {
                $filesLoading.hide();
            }
        });
    }

    /**
     * Render uploaded files list
     */
    function renderUploadedFilesList(data) {
        const files = data.files || [];
        const count = data.count || 0;
        const totalSize = data.formatted_total_size || '0 Bytes';

        // Update counters
        $filesCount.text(`${count} file${count !== 1 ? 's' : ''}`);
        $totalSize.text(totalSize);

        if (files.length === 0) {
            showEmptyState();
            return;
        }

        // Clear existing list
        $uploadedFilesList.empty();

        // Add each file to the list
        files.forEach(file => {
            const fileItem = createUploadedFileItem(file);
            $uploadedFilesList.append(fileItem);
        });

        // Debug: check parse buttons
        console.log('Files loaded. Parse buttons found:', $('.parse-file-btn').length);
        if ($('.parse-file-btn').length > 0) {
            console.log('First parse button HTML:', $('.parse-file-btn').first().prop('outerHTML'));
        }

        // Show the list
        $filesLoading.hide();
        $filesEmpty.hide();
        $filesListContainer.show();
    }

    /**
     * Create uploaded file list item HTML
     */
    function createUploadedFileItem(file) {
        const fileIcon = getFileIcon(file.extension);
        const fileName = escapeHtml(file.filename);
        const fileSize = file.formatted_size || formatFileSize(file.size);
        const fileModified = file.formatted_modified || 'Unknown';
        const fileUrl = file.url || `/uploads/${file.filename}`;
        const isParsed = file.parsed || false;
        const textLength = file.text_length || 0;
        const effectivelyParsed = isParsed && textLength > 0;
        const extractionMethod = file.extraction_method || 'spacy';
        const extractionMethodBadge = effectivelyParsed ?
            `<span class="badge ${extractionMethod === 'llm' ? 'bg-info' : 'bg-secondary'} ms-2" title="Extraction method: ${extractionMethod}">${extractionMethod.toUpperCase()}</span>` : '';

        return `
            <div class="list-group-item file-list-item uploaded-file-item"
                 data-filename="${escapeHtml(file.filename)}"
                 data-parsed="${effectivelyParsed}"
                 data-extraction-method="${extractionMethod}"
                 style="cursor: pointer;">
                <div class="file-info">
                    <div class="file-icon ${file.extension.substring(1)}-file">
                        <i class="${fileIcon}"></i>
                    </div>
                    <div class="file-details">
                        <div class="file-name">
                            <a href="${fileUrl}" target="_blank" class="text-decoration-none text-dark" onclick="event.stopPropagation();">
                                ${fileName}
                            </a>
                            ${effectivelyParsed ? '<span class="badge bg-success ms-2">Parsed</span>' : ''}
                            ${extractionMethodBadge}
                        </div>
                        <div class="d-flex justify-content-between">
                            <div class="file-size text-muted">${fileSize}</div>
                            <div class="file-modified text-muted small">${fileModified}</div>
                        </div>
                    </div>
                </div>
                <div class="file-actions">
                    <button class="btn btn-sm btn-outline-warning parse-file-btn"
                            title="Parse document to extract knowledge (can re-parse anytime)">
                        <i class="fas fa-cogs"></i> Parse
                    </button>
                    <button class="btn btn-sm btn-outline-info show-nodes-btn"
                            title="Show knowledge graph nodes">
                        <i class="fas fa-project-diagram"></i> 查看图谱
                    </button>
                    <a href="${fileUrl}" class="btn btn-sm btn-outline-primary"
                       download="${fileName}" title="Download" onclick="event.stopPropagation();">
                        <i class="fas fa-download"></i>
                    </a>
                    <button class="btn btn-sm btn-outline-danger delete-file-btn"
                            title="Delete file from server">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
                <!-- Progress container (hidden by default) -->
                <div class="file-progress-container mt-2 d-none">
                    <!-- Progress bar will be inserted here by updateFileItemProgressUI -->
                </div>
                <!-- Result container (hidden by default) -->
                <div class="file-result-container mt-2 d-none">
                    <!-- Parsing result report will be inserted here by createParsingResultReport -->
                </div>
            </div>
        `;
    }

    /**
     * Update progress UI for a file list item
     * @param {jQuery} $fileItem - File list item jQuery object
     * @param {Object} progress - Progress data from progress tracker
     */
    function updateFileItemProgressUI($fileItem, progress) {
        console.log('updateFileItemProgressUI called:', progress);
        console.log('Task ID:', progress.task_id, 'Status:', progress.status, 'Progress:', progress.progress);
        console.log('Progress keys:', Object.keys(progress));

        const $progressContainer = $fileItem.find('.file-progress-container');
        const $resultContainer = $fileItem.find('.file-result-container');
        console.log('Progress container found:', $progressContainer.length, 'Result container found:', $resultContainer.length);

        // Hide result container if visible
        $resultContainer.addClass('d-none').empty();

        // Show progress container
        $progressContainer.removeClass('d-none');
        console.log('Progress container classes after removing d-none:', $progressContainer.attr('class'));
        console.log('Progress container is visible:', $progressContainer.is(':visible'));
        console.log('Progress container HTML:', $progressContainer.html());

        // Create progress bar HTML using ProgressTracker class
        console.log('Checking ProgressTracker.createProgressBar availability...');
        let progressBarHtml;
        if (window.ProgressTracker && window.ProgressTracker.createProgressBar) {
            console.log('Using ProgressTracker.createProgressBar');
            try {
                progressBarHtml = window.ProgressTracker.createProgressBar(progress);
                console.log('createProgressBar result length:', progressBarHtml.length);
            } catch (error) {
                console.error('Error in createProgressBar:', error);
                progressBarHtml = createFallbackProgressBar(progress);
            }
        } else if (window.progressTracker && window.progressTracker.constructor && window.progressTracker.constructor.createProgressBar) {
            console.log('Using progressTracker.constructor.createProgressBar');
            try {
                progressBarHtml = window.progressTracker.constructor.createProgressBar(progress);
                console.log('createProgressBar result length:', progressBarHtml.length);
            } catch (error) {
                console.error('Error in constructor.createProgressBar:', error);
                progressBarHtml = createFallbackProgressBar(progress);
            }
        } else {
            console.log('Using fallback progress bar');
            progressBarHtml = createFallbackProgressBar(progress);
        }

        // Add cancel button if task is running
        let actionHtml = '';
        if (progress.status === 'running') {
            actionHtml = `
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-danger cancel-parsing-btn"
                            data-task-id="${progress.task_id}"
                            onclick="event.stopPropagation();">
                        <i class="fas fa-times me-1"></i>Cancel
                    </button>
                </div>
            `;
        }

        $progressContainer.html(progressBarHtml + actionHtml);

        // Update file item data attribute for status
        $fileItem.data('parsing-status', progress.status);

        // If task is completed, call completion handler
        if (progress.status === 'completed') {
            handleParsingComplete($fileItem, progress);
        }
        // If task failed or cancelled, call error handler
        else if (progress.status === 'failed' || progress.status === 'cancelled') {
            handleParsingError($fileItem, progress);
        }

        console.log('updateFileItemProgressUI finished for task:', progress.task_id);
    }

    /**
     * Handle parsing completion
     * @param {jQuery} $fileItem - File list item jQuery object
     * @param {Object} progress - Progress data with result
     */
    function handleParsingComplete($fileItem, progress) {
        const filename = $fileItem.data('filename');
        const extractionMethod = progress.extraction_method || currentExtractionMethod || 'spacy';

        // Update file item data
        $fileItem.data('parsed', true);
        $fileItem.data('parsing-status', 'completed');
        $fileItem.data('extraction-method', extractionMethod);

        // Add badges
        const $fileName = $fileItem.find('.file-name');
        $fileName.find('.badge').remove(); // Remove any existing badges
        $fileName.append('<span class="badge bg-success ms-2">Parsed</span>');
        $fileName.append(`<span class="badge ${extractionMethod === 'llm' ? 'bg-info' : 'bg-secondary'} ms-2">${extractionMethod.toUpperCase()}</span>`);

        // Hide progress container
        $fileItem.find('.file-progress-container').addClass('d-none').empty();

        // Show result container with report
        const $resultContainer = $fileItem.find('.file-result-container');
        $resultContainer.removeClass('d-none');
        $resultContainer.html(createParsingResultReport(progress));

        // Update parse button to show re-parse option (don't remove it)
        const $parseBtn = $fileItem.find('.parse-file-btn');
        if ($parseBtn.length) {
            $parseBtn.prop('disabled', false);
            $parseBtn.html('<i class="fas fa-redo"></i> Re-parse');
        }

        // Update current document if this is the active one
        if (currentDocument === filename) {
            currentDocument = filename; // Already set, but ensures consistency
        }

        // Show success alert
        const entityCount = progress.result?.entity_count || 0;
        const relationCount = progress.result?.relationship_count || 0;
        showAlert('success', `文档 "${filename}" 解析成功。找到 ${entityCount} 个实体和 ${relationCount} 个关系。`);

        // Refresh file list to get updated parsing state (optional)
        // loadUploadedFiles();
    }

    /**
     * Create fallback progress bar HTML
     * @param {Object} progress - Progress data
     * @returns {string} HTML string for progress bar
     */
    function createFallbackProgressBar(progress) {
        const percent = Math.round(progress.progress * 100);
        const statusText = progress.status || 'Unknown';
        return `
            <div class="progress mt-1" style="height: 20px;">
                <div class="progress-bar bg-secondary"
                     role="progressbar"
                     style="width: ${percent}%;"
                     aria-valuenow="${percent}"
                     aria-valuemin="0"
                     aria-valuemax="100">
                    ${percent}% - ${statusText}
                </div>
            </div>`;
    }

    /**
     * Handle parsing error or cancellation
     * @param {jQuery} $fileItem - File list item jQuery object
     * @param {Object} progress - Progress data with error
     */
    function handleParsingError($fileItem, progress) {
        const filename = $fileItem.data('filename');
        const errorMessage = progress.error || '解析失败';

        // Hide progress container
        $fileItem.find('.file-progress-container').addClass('d-none').empty();

        // Show error in result container
        const $resultContainer = $fileItem.find('.file-result-container');
        $resultContainer.removeClass('d-none');
        // Escape error message for safe HTML insertion
        const escapedErrorMessage = escapeHtml(errorMessage);
        $resultContainer.html(`
            <div class="alert alert-danger alert-sm mb-0">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${escapedErrorMessage}
            </div>
        `);

        // Restore parse button to re-parse state
        const $parseBtn = $fileItem.find('.parse-file-btn');
        if ($parseBtn.length) {
            $parseBtn.prop('disabled', false);
            $parseBtn.html('<i class="fas fa-redo"></i> Re-parse');
        }

        // Show error alert
        showAlert('danger', `解析 "${filename}" 失败：${errorMessage}`);
    }

    /**
     * Create parsing result report HTML
     * @param {Object} progress - Progress data with result
     * @returns {string} HTML string for result report
     */
    function createParsingResultReport(progress) {
        const result = progress.result || {};
        const entityCount = result.entity_count || 0;
        const relationCount = result.relationship_count || 0;
        const textLength = result.text_length || 0;
        const wordCount = result.word_count || 0;

        // Escape all values for safe HTML insertion
        const escapedEntityCount = escapeHtml(String(entityCount));
        const escapedRelationCount = escapeHtml(String(relationCount));
        const escapedTextLength = escapeHtml(String(textLength));
        const escapedWordCount = escapeHtml(String(wordCount));

        let reportHtml = `
            <div class="parsing-result-summary">
                <div class="d-flex align-items-center">
                    <span class="badge bg-success me-2">
                        <i class="fas fa-check-circle me-1"></i>Parsed
                    </span>
                    <span class="small text-muted">
        `;

        // Add entity and relation counts if available
        if (entityCount > 0 || relationCount > 0) {
            reportHtml += `${escapedEntityCount} entities · ${escapedRelationCount} relations`;
        } else {
            reportHtml += `${escapedTextLength} chars · ${escapedWordCount} words`;
        }

        reportHtml += `
                    </span>
                </div>
            </div>
        `;

        return reportHtml;
    }

    /**
     * Cancel parsing for a file item
     * @param {string} taskId - Task ID to cancel
     * @param {jQuery} $fileItem - File list item jQuery object
     */
    function cancelParsingForFileItem(taskId, $fileItem) {
        if (!confirm('Are you sure you want to cancel this parsing task?')) {
            return;
        }

        if (window.progressTracker) {
            window.progressTracker.cancelTask(taskId)
                .then(() => {
                    showAlert('success', '解析已成功取消。');
                })
                .catch(error => {
                    console.error('Failed to cancel parsing:', error);
                    showAlert(`取消解析失败：${error.message}`, 'danger');
                });
        }
    }

    /**
     * Show empty state for file list
     */
    function showEmptyState() {
        $filesLoading.hide();
        $filesListContainer.hide();
        $filesEmpty.show();
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Event delegation for remove file buttons
    $(document).on('click', '.remove-file', function() {
        const index = $(this).data('index');
        selectedFiles.splice(index, 1);
        updateFileList();
    });

    // Enable navigation links for future phases
    $('#nav-graph, #nav-chat').on('click', function(e) {
        if ($(this).hasClass('disabled')) {
            e.preventDefault();
            showAlert('info', '此功能将在第二/第三阶段提供。');
        }
    });

    // Handle uploaded file item clicks for knowledge graph nodes
    $(document).on('click', '.uploaded-file-item', function(e) {
        // Don't trigger if clicking on buttons or links inside the item
        if ($(e.target).closest('.btn, a').length > 0) {
            return;
        }

        const filename = $(this).data('filename');
        const isParsed = $(this).data('parsed');

        if (!isParsed) {
            showAlert('info', '此文件需要先解析以提取知识图谱节点。');
            return;
        }

        // Trigger custom event for node loading
        $(document).trigger('fileSelectedForNodes', [filename]);

        // Add visual feedback
        $('.uploaded-file-item').removeClass('active');
        $(this).addClass('active');

        // Update current document for chat
        currentDocument = filename;
    });

    // Handle parse file button clicks
    console.log('Binding parse-file-btn click handler');
    $(document).on('click', '.parse-file-btn', function(e) {
        console.log('Parse button clicked - event triggered');
        e.stopPropagation();

        const $fileItem = $(this).closest('.uploaded-file-item');
        const filename = $fileItem.data('filename');
        console.log('Filename:', filename);

        // Get selected extraction method from global selector
        const extractionMethod = currentExtractionMethod || 'spacy';
        console.log('Extraction method:', extractionMethod);

        // Disable button and show loading state
        const $button = $(this);
        const originalButtonHtml = $button.html();
        $button.prop('disabled', true);
        $button.html('<i class="fas fa-spinner fa-spin"></i> 正在解析...');

        console.log('Sending async parse request for:', filename);
        // Send async parse request with extraction method
        $.ajax({
            url: `/parse/async/${encodeURIComponent(filename)}`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ extraction_method: extractionMethod }),
            success: function(response) {
                console.log('Parse request success:', response);
                if (response.success) {
                    const taskId = response.task_id;
                    console.log('Task ID:', taskId);

                    // Start progress tracking
                    console.log('Checking window.progressTracker:', window.progressTracker);
                    if (window.progressTracker) {
                        console.log('Starting progress tracking for task:', taskId);
                        try {
                            window.progressTracker.startTracking(
                                taskId,
                                filename,
                                // onUpdate callback
                                function(progress) {
                                    updateFileItemProgressUI($fileItem, progress);
                                },
                                // onComplete callback
                                function(progress) {
                                    // Restore button on complete
                                    $button.prop('disabled', false);
                                    $button.html('<i class="fas fa-redo"></i> Re-parse');
                                    updateFileItemProgressUI($fileItem, progress);
                                },
                                // onError callback
                                function(progress) {
                                    // Restore button on error
                                    $button.prop('disabled', false);
                                    $button.html('<i class="fas fa-redo"></i> Re-parse');
                                }
                            );
                        } catch (error) {
                            console.error('Failed to start progress tracking:', error);
                            showAlert('danger', '启动进度跟踪失败。解析可能仍在后台运行。');
                            // Fallback: show generic progress
                            $fileItem.find('.file-progress-container').removeClass('d-none').html(`
                                <div class="progress mt-1" style="height: 20px;">
                                    <div class="progress-bar bg-info progress-bar-striped progress-bar-animated"
                                         role="progressbar"
                                         style="width: 50%;"
                                         aria-valuenow="50"
                                         aria-valuemin="0"
                                         aria-valuemax="100">
                                        50% - 处理中
                                    </div>
                                </div>
                                <small class="text-muted">解析进行中（进度跟踪错误）</small>
                            `);
                        }
                    } else {
                        console.error('Progress tracker not available');
                        showAlert('danger', '进度跟踪不可用。解析已在后台启动。');
                        // Fallback: show generic progress
                        $fileItem.find('.file-progress-container').removeClass('d-none').html(`
                            <div class="progress mt-1" style="height: 20px;">
                                <div class="progress-bar bg-info progress-bar-striped progress-bar-animated"
                                     role="progressbar"
                                     style="width: 50%;"
                                     aria-valuenow="50"
                                     aria-valuemin="0"
                                     aria-valuemax="100">
                                    50% - Processing
                                </div>
                            </div>
                            <small class="text-muted">解析进行中（进度跟踪不可用）</small>
                        `);
                    }

                    // Show initial progress state
                    updateFileItemProgressUI($fileItem, {
                        task_id: taskId,
                        filename: filename,
                        status: 'pending',
                        progress: 0.1,
                        step_description: '正在启动解析流程...'
                    });

                    showAlert('info', `已开始解析 "${filename}"。进度将在下方显示。`);
                } else {
                    showAlert('danger', `启动解析 "${filename}" 失败：${response.error || '未知错误'}`);
                    $button.prop('disabled', false);
                    $button.html('<i class="fas fa-redo"></i> Re-parse');
                }
            },
            error: function(xhr) {
                let errorMessage = '启动解析失败，请重试。';
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMessage = response.error || errorMessage;
                } catch (e) {
                    // Use default error message
                }
                showAlert('danger', errorMessage);
                $button.prop('disabled', false);
                $button.html('<i class="fas fa-cogs"></i>');
            }
        });
    });

    // Handle cancel parsing button clicks
    $(document).on('click', '.cancel-parsing-btn', function(e) {
        e.stopPropagation();

        const $button = $(this);
        const taskId = $button.data('task-id');
        const $fileItem = $button.closest('.uploaded-file-item');

        cancelParsingForFileItem(taskId, $fileItem);
    });

    // Handle show nodes button clicks
    $(document).on('click', '.show-nodes-btn', function(e) {
        e.stopPropagation();

        const $fileItem = $(this).closest('.uploaded-file-item');
        const filename = $fileItem.data('filename');
        const isParsed = $fileItem.data('parsed');

        console.log('=== Show Nodes Button Clicked ===');
        console.log('Filename:', filename);
        console.log('Is Parsed:', isParsed);

        if (!isParsed) {
            showAlert('info', '此文件需要先解析以提取知识图谱节点。');
            return;
        }

        // Trigger custom event for node loading
        console.log('Triggering fileSelectedForNodes event with filename:', filename);
        $(document).trigger('fileSelectedForNodes', [filename]);

        // Add visual feedback
        $('.uploaded-file-item').removeClass('active');
        $fileItem.addClass('active');

        // Update current document for chat
        currentDocument = filename;
        console.log('currentDocument set to:', currentDocument);
    });

    // Handle delete file button clicks
    console.log('Binding delete-file-btn click handler');
    $(document).on('click', '.delete-file-btn', function(e) {
        e.stopPropagation();

        const $fileItem = $(this).closest('.uploaded-file-item');
        const filename = $fileItem.data('filename');
        console.log('=== Delete File ===');
        console.log('Filename from data attribute:', filename);
        console.log('File item element:', $fileItem[0]);

        // Confirm deletion
        if (!confirm(`Are you sure you want to delete "${filename}"?\n\nThis will also delete all parsed data and knowledge graph data associated with this file.`)) {
            return;
        }

        // Disable button and show loading state
        const $button = $(this);
        const originalHtml = $button.html();
        $button.prop('disabled', true);
        $button.html('<i class="fas fa-spinner fa-spin"></i>');

        console.log('Sending DELETE request to:', `/api/files/${encodeURIComponent(filename)}`);
        $.ajax({
            url: `/api/files/${encodeURIComponent(filename)}`,
            type: 'DELETE',
            contentType: 'application/json',
            success: function(response) {
                console.log('Delete response:', response);
                if (response.success) {
                    console.log('Delete successful, removing element from DOM');
                    console.log('File item before remove:', $fileItem.length);

                    // Add visual feedback class
                    $fileItem.addClass('deleting');

                    // Immediately hide the element
                    $fileItem.slideUp(300, function() {
                        console.log('SlideUp callback executed');
                        $(this).remove();

                        // Update file count
                        const $filesCount = $('#filesCount');
                        const currentCount = parseInt($filesCount.text().match(/\d+/)?.[0] || '0');
                        if (currentCount > 0) {
                            $filesCount.text(`${currentCount - 1} file${currentCount - 1 !== 1 ? 's' : ''}`);
                        }

                        console.log('File item removed, count updated');
                        showAlert('success', `文件 "${filename}" 已成功删除。`);
                    });
                } else {
                    console.log('Delete failed:', response.error);
                    showAlert('danger', `删除 "${filename}" 失败：${response.error || '未知错误'}`);
                    $button.prop('disabled', false);
                    $button.html(originalHtml);
                }
            },
            error: function(xhr, status, error) {
                console.error('Delete error:', status, error);
                console.error('Response text:', xhr.responseText);
                let errorMessage = '删除文件失败，请重试。';
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMessage = response.error || errorMessage;
                } catch (e) {
                    // Use default error message
                }
                showAlert('danger', errorMessage);
                $button.prop('disabled', false);
                $button.html(originalHtml);
            }
        });
    });

    // ====================
    // Chat Functionality
    // ====================

    const $chatMessages = $('#chatMessages');
    const $chatInput = $('#chatInput');
    const $sendMessageBtn = $('#sendMessageBtn');
    const $clearChatBtn = $('#clearChatBtn');
    const $toggleChatBtn = $('#toggleChatBtn');

    let chatHistory = [];

    // 发送消息
    $sendMessageBtn.on('click', sendMessage);
    $chatInput.on('keypress', function(e) {
        if (e.which === 13 && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 清除聊天历史
    $clearChatBtn.on('click', clearChatHistory);

    // 切换聊天窗口显示
    $toggleChatBtn.on('click', function() {
        $('.chat-window .card-body, .chat-window .card-footer').toggle();
        $(this).html($('.chat-window .card-body').is(':visible') ?
            '<i class="fas fa-minus"></i>' : '<i class="fas fa-plus"></i>');
    });

    function sendMessage() {
        const message = $chatInput.val().trim();
        if (!message) return;

        // 添加用户消息到界面
        addMessage('user', message);
        $chatInput.val('');

        // 发送到后端
        $.ajax({
            url: '/chat/ask',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                question: message,
                document_id: currentDocument || null, // 当前选中的文档
                chat_history: chatHistory.slice(-5) // 最近5条历史
            }),
            success: function(response) {
                if (response.success) {
                    addMessage('assistant', response.answer);
                    // 更新聊天历史
                    chatHistory.push({ role: 'user', content: message });
                    chatHistory.push({ role: 'assistant', content: response.answer });
                } else {
                    addMessage('assistant', `错误：${response.error}`);
                }
            },
            error: function() {
                addMessage('assistant', '抱歉，处理您的问题时发生错误。');
            }
        });
    }

    function addMessage(role, content) {
        const timestamp = new Date().toLocaleTimeString();
        const messageHtml = `
            <div class="message ${role}">
                <div class="message-header">
                    <strong>${role === 'user' ? 'You' : 'Assistant'}</strong>
                    <small class="text-muted">${timestamp}</small>
                </div>
                <div class="message-content">${escapeHtml(content)}</div>
            </div>
        `;
        $chatMessages.append(messageHtml);
        $chatMessages.scrollTop($chatMessages[0].scrollHeight);
    }

    function clearChatHistory() {
        if (confirm('Clear all chat history?')) {
            $chatMessages.html(`
                <div class="message assistant">
                    <div class="message-header">
                        <strong>Assistant</strong>
                        <small class="text-muted">Just now</small>
                    </div>
                    <div class="message-content">
                        Chat history cleared. How can I help you?
                    </div>
                </div>
            `);
            chatHistory = [];
        }
    }
});