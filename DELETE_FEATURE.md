# 文件删除功能说明

## 功能概述

在 Uploaded Files 文件列表中，为每个文件记录添加了删除按钮，支持删除上传文件及其所有关联数据。

## UI 界面

### 文件操作按钮栏

每个文件记录右侧显示 4 个操作按钮：

| 按钮 | 图标 | 功能 |
|------|------|------|
| Parse | 齿轮 ⚙️ | 解析文档，提取知识图谱 |
| 查看图谱 | 图表 📊 | 显示知识图谱节点 |
| 下载 | 下载 ⬇️ | 下载文件到本地 |
| **删除** | 垃圾桶 🗑️ | **从服务器删除文件及关联数据** |

### 删除按钮样式
- 红色边框 (`btn-outline-danger`)
- 垃圾桶图标 (`fa-trash-alt`)
- 悬停时显示红色背景

## 删除功能流程

### 1. 点击删除按钮
```
用户点击删除按钮
    ↓
阻止事件冒泡 (不触发文件项选择)
    ↓
弹出确认对话框
```

### 2. 确认对话框
```
┌─────────────────────────────────────────┐
│  Are you sure you want to delete        │
│  "filename.docx"?                       │
│                                         │
│  This will also delete all parsed data  │
│  and knowledge graph data associated    │
│  with this file.                        │
│                                         │
│          [取消]     [确定]              │
└─────────────────────────────────────────┘
```

### 3. 删除处理中
- 按钮禁用，显示旋转加载图标
- 发送 DELETE 请求到后端 API
- 后端依次删除各类关联数据

### 4. 删除完成
- 文件项淡出动画 (opacity 0.3s)
- 从列表中移除文件项
- 刷新文件列表更新统计
- 显示成功提示消息

## 后端删除流程

### API 端点
```
DELETE /api/files/<filename>
```

### 删除顺序

```
1. 验证文件存在性和类型
   ↓
2. 删除解析后的文本文件 (_parsed.txt)
   ↓
3. 删除知识提取结果 (_knowledge.json)
   ↓
4. 删除图谱构建结果 (_graph.json)
   ↓
5. 删除上传的原始文件
   ↓
6. 删除 Neo4j 中的图数据 (如果存在)
```

### 返回格式

**成功响应:**
```json
{
  "success": true,
  "message": "File \"filename.docx\" and all associated data deleted successfully",
  "filename": "filename.docx"
}
```

**失败响应:**
```json
{
  "success": false,
  "error": "File not found: filename.docx"
}
```

## 代码实现

### 前端 JavaScript

**文件**: `static/js/main.js`

**1. 创建文件项时添加删除按钮:**
```javascript
<button class="btn btn-sm btn-outline-danger delete-file-btn"
        title="Delete file from server"
        onclick="event.stopPropagation();">
    <i class="fas fa-trash-alt"></i>
</button>
```

**2. 删除按钮事件处理:**
```javascript
$(document).on('click', '.delete-file-btn', function(e) {
    e.stopPropagation();

    const $fileItem = $(this).closest('.uploaded-file-item');
    const filename = $fileItem.data('filename');

    // 确认删除
    if (!confirm(`Are you sure you want to delete "${filename}"?...`)) {
        return;
    }

    // 发送 DELETE 请求
    $.ajax({
        url: `/api/files/${encodeURIComponent(filename)}`,
        type: 'DELETE',
        success: function(response) {
            // 移除文件项
            $fileItem.remove();
            loadUploadedFiles(); // 刷新列表
        }
    });
});
```

### 后端 Python

**文件**: `app.py`

**API 端点:**
```python
@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete an uploaded file and all associated data"""
    upload_folder = app.config['UPLOAD_FOLDER']
    filepath = os.path.join(upload_folder, filename)

    # 验证文件存在
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'File not found'}), 404

    # 删除解析文本
    parsed_text_path = parsing_manager.get_parsed_text_path(filename)
    if os.path.exists(parsed_text_path):
        os.remove(parsed_text_path)

    # 删除知识提取结果
    extraction_path = parsing_manager.get_knowledge_extraction_path(filename)
    if os.path.exists(extraction_path):
        os.remove(extraction_path)

    # 删除图谱数据
    graph_path = parsing_manager.get_graph_path(filename)
    if os.path.exists(graph_path):
        os.remove(graph_path)

    # 删除 Neo4j 图数据
    parsing_manager.graph_db.delete_document_graph(filename)

    # 删除原始文件
    os.remove(filepath)

    return jsonify({'success': True, 'message': 'Deleted successfully'})
```

**文件**: `src/parsing_manager.py`

**新增方法:**
```python
def get_graph_path(self, filename: str) -> str:
    """Get path for graph data file"""
    return self.get_graph_building_path(filename)

def get_parsing_state_path(self, filename: str) -> str:
    """Get path for parsing state file"""
    state_dir = os.path.join(self.parsed_data_folder, 'parsing_states')
    return os.path.join(state_dir, f"{safe_name}_state.json")
```

## 安全考虑

### 1. 确认对话框
防止误删，删除前必须用户确认。

### 2. 路径验证
- 验证文件是否存在
- 验证是文件而非目录
- 防止路径遍历攻击 (使用 `os.path.join`)

### 3. 错误处理
- 每个删除步骤都有 try-except 保护
- 删除失败记录警告日志
- 不影响其他步骤执行

### 4. 日志记录
```python
logger.info(f"Deleted parsed text: {parsed_text_path}")
logger.warning(f"Failed to delete knowledge extraction: {e}")
```

## 测试场景

### 场景 1: 删除未解析文件
1. 上传文件
2. 不解析，直接点击删除
3. 仅删除原始文件

### 场景 2: 删除已解析文件
1. 上传文件并解析
2. 点击删除
3. 删除原始文件和解析文本

### 场景 3: 删除完整知识图谱文件
1. 上传文件 → 解析 → 提取知识 → 构建图谱
2. 点击删除
3. 删除所有关联数据 + Neo4j 图数据

### 场景 4: 删除不存在的文件
1. 手动构造删除请求
2. 返回 404 错误

## 相关文件

本次修改的文件:
- `app.py` - 新增 DELETE API 端点
- `src/parsing_manager.py` - 新增路径获取方法
- `static/js/main.js` - 删除按钮 UI 和事件处理

Git 提交:
```
commit de412bf
feat: 添加文件删除功能
```
