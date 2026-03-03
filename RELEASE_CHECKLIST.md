# 发布前检查清单

## 已完成的功能

### 1. 配置管理系统 ✅
- [x] 配置管理器 (`config/config_manager.py`)
- [x] AES 加密存储敏感信息
- [x] Web 配置页面 (`/settings`)
- [x] 配置验证 API（测试连接）
- [x] 恢复默认配置功能

### 2. 前端页面 ✅
- [x] 配置页面 (`templates/settings.html`)
- [x] 独立聊天页面 (`templates/chat.html`)
- [x] 导航栏更新（添加"设置"入口）

### 3. API 端点 ✅
- [x] `GET/POST /api/config` - 获取/保存配置
- [x] `POST /api/config/validate` - 验证配置
- [x] `POST /api/config/reset` - 恢复默认
- [x] `GET /settings` - 配置页面
- [x] `GET /chat` - 聊天页面

### 4. 安全优化 ✅
- [x] 删除 `DEEPSEEK_CONFIG.md`（含敏感 API Key）
- [x] 清理代码中硬编码的敏感信息
- [x] 更新 `.gitignore` 排除配置文件
- [x] 创建 `.env.example` 模板
- [x] 清理测试文件中的敏感信息

### 5. 文档更新 ✅
- [x] README.md 完整更新
- [x] 添加项目负责人：Kevin Lee
- [x] 补充配置说明和使用指南
- [x] 添加安全说明

---

## 发布前步骤

### 1. 检查敏感信息

```bash
# 搜索代码中是否还有硬编码的 Key
grep -r "sk-[a-zA-Z0-9]+" --include="*.py" --include="*.md" .

# 检查配置文件
cat .gitignore  # 确保包含 .env 和 config/
```

**预期结果**: 除了 `.env.example` 中的示例外，不应出现真实 API Key

### 2. 验证配置功能

```bash
# 启动应用
python app.py

# 访问配置页面
http://localhost:5000/settings

# 测试以下功能:
- [ ] 填写 LLM API 配置
- [ ] 填写 Neo4j 配置
- [ ] 点击"保存配置"
- [ ] 点击"测试连接"
- [ ] 验证配置是否正确保存
```

### 3. 检查文件列表

```bash
# 查看即将提交的文件
git status

# 确保以下文件 NOT 被提交:
# - .env
# - config/user_config.json
# - config/.encryption_key
# - *.log
```

### 4. 更新版本号

在 `README.md` 中更新版本号：
```
### v1.0.0 (2026-03-03)
```

### 5. 创建 LICENSE 文件

如果没有 LICENSE 文件：
```bash
# MIT License
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2026 Kevin Lee

Permission is hereby granted...
EOF
```

### 6. 创建 .github/workflows (可选)

如果需要 CI/CD：
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest
```

---

## 安全检查清单

### 敏感信息
- [ ] 代码中没有硬编码的 API Key
- [ ] 代码中没有硬编码的密码
- [ ] `.env` 文件在 `.gitignore` 中
- [ ] `config/user_config.json` 在 `.gitignore` 中
- [ ] `config/.encryption_key` 在 `.gitignore` 中
- [ ] 日志文件中没有泄露敏感信息

### 配置安全
- [ ] 加密密钥文件权限设置为 600（仅所有者可读写）
- [ ] 生产环境使用强 SECRET_KEY
- [ ] CORS 配置正确（如果跨域）

### 依赖安全
```bash
# 检查依赖漏洞
pip install pip-audit
pip-audit -r requirements.txt
```

---

## 发布到 GitHub

### 1. 创建 GitHub 仓库

```bash
# 如果还没有远程仓库
git remote add origin https://github.com/your-username/kg-agent-demo.git
```

### 2. 推送代码

```bash
# 推送到主分支
git push -u origin master

# 或者如果使用 main 分支
git branch -M main
git push -u origin main
```

### 3. 创建 Release

在 GitHub 上：
1. 访问 https://github.com/your-username/kg-agent-demo/releases
2. 点击 "Create a new release"
3. Tag version: `v1.0.0`
4. Release title: `v1.0.0 - Initial Release`
5. 描述功能列表
6. 点击 "Publish release"

### 4. 更新 GitHub 仓库描述

在 GitHub 仓库设置中：
- 添加网站链接
- 添加主题标签：`knowledge-graph` `llm` `rag` `neo4j` `flask`

---

## 用户使用流程

### 首次使用

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd kg-agent-demo
   ```

2. **安装依赖**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   python -m spacy download zh_core_web_sm
   ```

3. **启动应用**
   ```bash
   python app.py
   ```

4. **配置应用**
   - 访问 http://localhost:5000/settings
   - 填写 LLM API 和 Neo4j 配置
   - 点击"测试连接"验证
   - 点击"保存配置"

5. **开始使用**
   - 上传文档
   - 等待解析完成
   - 在聊天窗口提问

---

## 常见问题

### Q: 配置保存在哪里？
A: `config/user_config.json`（加密存储）

### Q: 如何重置配置？
A: 访问 `/settings` 页面，点击"恢复默认"，或删除 `config/user_config.json`

### Q: 加密密钥在哪里？
A: `config/.encryption_key` - 请勿丢失，否则无法解密配置

### Q: 可以手动编辑配置吗？
A: 可以编辑 `config/user_config.json`，但敏感字段会被加密

---

**最后更新**: 2026-03-03
**版本**: v1.0.0
