# 开发指南

> 📚 **完整开发文档请查看**：[docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md)

本文档提供简化的快速开始指南。详细的开发规范、测试指南、调试技巧等内容请参阅上方链接。

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Vae-Scrooge/remote-cmd-test.git
cd remote-cmd-test
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate
```

### 3. 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 4. 运行测试

```bash
pytest tests/ -v
```

---

## 项目结构

```
remote-cmd-test/
├── remote_cmd/          # 主代码包
│   ├── core/            # 核心功能（SSHClient、HostManager）
│   ├── cli/             # 命令行接口
│   └── utils/           # 工具模块
├── tests/               # 测试代码
├── docs/                # 文档
│   └── DEVELOPMENT.md   # ← 完整开发指南
└── examples/            # 示例代码
```

---

## 代码规范

- **格式化**：`black remote_cmd/ tests/`
- **代码检查**：`flake8 remote_cmd/ tests/`
- **类型检查**：`mypy remote_cmd/`
- **测试**：`pytest tests/ -v --cov=remote_cmd`

---

## 相关文档

- [完整开发指南](./docs/DEVELOPMENT.md) - 详细开发规范、发布流程
- [API 文档](./docs/API.md) - API 参考
- [架构文档](./docs/architecture.md) - 系统架构设计
- [贡献指南](./CONTRIBUTING.md) - 如何贡献代码

---

**欢迎参与开发！** 🚀
