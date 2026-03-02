# 解析按钮始终显示功能 - 实现说明

## 修改内容

### 1. JavaScript 修改 (`static/js/main.js`)

#### `createUploadedFileItem` 函数
**修改前**: 只有未解析的文件才显示解析按钮
```javascript
${!effectivelyParsed ? `
<button class="btn btn-sm btn-outline-warning parse-file-btn">...</button>
` : ''}
```

**修改后**: 所有文件都显示解析按钮，支持重新解析
```javascript
<button class="btn btn-sm btn-outline-warning parse-file-btn"
        title="Parse document to extract knowledge (can re-parse anytime)">
    <i class="fas fa-cogs"></i> Parse
</button>
```

同时添加了提取方法徽章显示：
```javascript
const extractionMethodBadge = effectivelyParsed ?
    `<span class="badge ${extractionMethod === 'llm' ? 'bg-info' : 'bg-secondary'} ms-2">
        ${extractionMethod.toUpperCase()}
    </span>` : '';
```

#### `handleParsingComplete` 函数
**修改前**: 解析完成后移除按钮
```javascript
$fileItem.find('.parse-file-btn').remove();
```

**修改后**: 解析完成后更新按钮为"Re-parse"
```javascript
const $parseBtn = $fileItem.find('.parse-file-btn');
if ($parseBtn.length) {
    $parseBtn.prop('disabled', false);
    $parseBtn.html('<i class="fas fa-redo"></i> Re-parse');
}
```

同时更新文件项的徽章显示：
```javascript
$fileName.append('<span class="badge bg-success ms-2">Parsed</span>');
$fileName.append(`<span class="badge ${extractionMethod === 'llm' ? 'bg-info' : 'bg-secondary'} ms-2">
    ${extractionMethod.toUpperCase()}
</span>`);
```

#### `handleParsingError` 函数
**修改前**: 错误时重新创建按钮
```javascript
$fileActions.prepend(`<button class="btn btn-sm btn-outline-warning parse-file-btn">...</button>`);
```

**修改后**: 错误时恢复按钮为"Re-parse"状态
```javascript
const $parseBtn = $fileItem.find('.parse-file-btn');
if ($parseBtn.length) {
    $parseBtn.prop('disabled', false);
    $parseBtn.html('<i class="fas fa-redo"></i> Re-parse');
}
```

#### 解析按钮点击处理
**修改前**: 点击后隐藏按钮
```javascript
$button.hide(); // Hide but keep in DOM
```

**修改后**: 点击后显示加载状态，完成后恢复
```javascript
$button.prop('disabled', true);
$button.html('<i class="fas fa-spinner fa-spin"></i> Parsing...');

// 在 onComplete 回调中恢复
$button.prop('disabled', false);
$button.html('<i class="fas fa-redo"></i> Re-parse');
```

## UI 变化

### 文件列表项显示

**未解析文件**:
```
[文件名] [Parse 按钮] [图表图标按钮] [下载按钮]
```

**已解析文件 (spaCy)**:
```
[文件名] [Parsed✓] [SPACY] [Re-parse 按钮] [图表图标按钮] [下载按钮]
```

**已解析文件 (LLM)**:
```
[文件名] [Parsed✓] [LLM] [Re-parse 按钮] [图表图标按钮] [下载按钮]
```

### 按钮状态

| 状态 | 按钮文本 | 图标 | 可点击 |
|------|---------|------|--------|
| 初始 | Parse | cogs | 是 |
| 解析中 | Parsing... | spinner | 否 |
| 已完成 | Re-parse | redo | 是 |
| 失败 | Re-parse | redo | 是 |

## 使用流程

1. **上传文件** → 文件列表显示，所有文件都有"Parse"按钮
2. **选择提取方法** → 从顶部下拉框选择 spaCy 或 LLM API
3. **点击 Parse** → 按钮变为"Parsing..."，显示进度条
4. **解析完成** → 按钮变为"Re-parse"，显示 Parsed 徽章和方法徽章
5. **切换方法重新解析** → 选择另一种方法，点击"Re-parse"即可

## 优势

1. **操作一致性**: 按钮始终可见，用户知道可以随时重新解析
2. **方法对比**: 可以轻松使用不同方法解析同一文档，对比结果
3. **错误恢复**: 解析失败后按钮自动恢复，无需刷新页面
4. **状态清晰**: 徽章显示解析状态和使用的提取方法

## 相关文件

修改的文件:
- `static/js/main.js` - 核心逻辑修改

不需要修改的文件:
- `templates/index.html` - UI 选择器已在之前实现
- `app.py` - 后端 API 已支持 extraction_method 参数
- `src/parsing_manager.py` - 已支持动态提取方法
