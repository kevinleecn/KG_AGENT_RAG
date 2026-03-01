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

    // File tracking
    let selectedFiles = [];
    let currentDocument = null;

    // Initialize
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
            showAlert('info', 'File list refreshed.');
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
            showAlert('warning', 'No valid files selected. Please select .txt, .docx, .pdf, or .pptx files.');
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
            showAlert('warning', 'No files selected.');
            return;
        }

        // Disable upload button and show loading state
        $uploadBtn.prop('disabled', true);
        $uploadBtn.html('<i class="fas fa-spinner fa-spin me-2"></i>Uploading...');

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
                $uploadBtn.html('<i class="fas fa-upload me-2"></i>Upload Files');
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
            showAlert('danger', response.error || 'Upload failed.');
        }
    }

    /**
     * Handle upload error
     */
    function handleUploadError(xhr) {
        let errorMessage = 'Upload failed. Please try again.';

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
                    showAlert('danger', 'Failed to load file list: ' + (response.error || 'Unknown error'));
                    showEmptyState();
                }
            },
            error: function(xhr) {
                let errorMessage = 'Failed to load file list. Please try again.';
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

        return `
            <div class="list-group-item file-list-item uploaded-file-item"
                 data-filename="${escapeHtml(file.filename)}"
                 data-parsed="${isParsed}"
                 style="cursor: pointer;">
                <div class="file-info">
                    <div class="file-icon ${file.extension.substring(1)}-file">
                        <i class="${fileIcon}"></i>
                    </div>
                    <div class="file-details">
                        <div class="file-name">
                            <a href="${fileUrl}" target="_blank" class="text-decoration-none" onclick="event.stopPropagation();">
                                ${fileName}
                            </a>
                            ${isParsed ? '<span class="badge bg-success ms-2">Parsed</span>' : ''}
                        </div>
                        <div class="d-flex justify-content-between">
                            <div class="file-size text-muted">${fileSize}</div>
                            <div class="file-modified text-muted small">${fileModified}</div>
                        </div>
                    </div>
                </div>
                <div class="file-actions">
                    <button class="btn btn-sm btn-outline-info show-nodes-btn"
                            title="Show knowledge graph nodes"
                            onclick="event.stopPropagation();">
                        <i class="fas fa-project-diagram"></i>
                    </button>
                    <a href="${fileUrl}" class="btn btn-sm btn-outline-primary"
                       download="${fileName}" title="Download" onclick="event.stopPropagation();">
                        <i class="fas fa-download"></i>
                    </a>
                </div>
            </div>
        `;
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
            showAlert('info', 'This feature will be available in Phase 2/3.');
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
            showAlert('info', 'This file needs to be parsed first to extract knowledge graph nodes.');
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

    // Handle show nodes button clicks
    $(document).on('click', '.show-nodes-btn', function(e) {
        e.stopPropagation();

        const $fileItem = $(this).closest('.uploaded-file-item');
        const filename = $fileItem.data('filename');
        const isParsed = $fileItem.data('parsed');

        if (!isParsed) {
            showAlert('info', 'This file needs to be parsed first to extract knowledge graph nodes.');
            return;
        }

        // Trigger custom event for node loading
        $(document).trigger('fileSelectedForNodes', [filename]);

        // Add visual feedback
        $('.uploaded-file-item').removeClass('active');
        $fileItem.addClass('active');

        // Update current document for chat
        currentDocument = filename;
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
                    addMessage('assistant', `Error: ${response.error}`);
                }
            },
            error: function() {
                addMessage('assistant', 'Sorry, there was an error processing your question.');
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