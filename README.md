# Remote CMD

一个基于 Python 的 SSH 远程服务器管理工具，为系统管理员和开发者提供简洁高效的远程服务器管理体验。

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)

## 特性

- 🚀 **简单易用** - 直观的命令行界面，快速上手
- 🔐 **安全连接** - 支持密码和 SSH Key 认证
- 📁 **文件传输** - 便捷的文件上传和下载功能
- 🖥️ **命令执行** - 远程执行命令并获取实时输出
- 📝 **主机管理** - 统一管理多台服务器配置
- 🏷️ **标签系统** - 为主机打标签，方便分类管理
- 🔍 **连接测试** - 快速测试服务器连通性

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/Vae-Scrooge/remote-cmd-test.git
cd remote-cmd-test

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 配置

1. 复制示例配置文件：
```bash
cp config.example.yaml config.yaml
```

2. 编辑 `config.yaml`，根据需要调整配置项。

### 使用

#### 添加主机

```bash
# 使用密码认证
python -m remote_cmd host add my-server 192.168.1.100 admin --password mypassword

# 使用 SSH Key
python -m remote_cmd host add my-server 192.168.1.100 admin --key ~/.ssh/id_rsa

# 添加标签
python -m remote_cmd host add my-server 192.168.1.100 admin --key ~/.ssh/id_rsa --tag production --tag web
```

#### 查看主机列表

```bash
python -m remote_cmd host list

# 按标签筛选
python -m remote_cmd host list --tag production
```

#### 执行远程命令

```bash
python -m remote_cmd run my-server "ls -la"

python -m remote_cmd run my-server "systemctl status nginx"
```

#### 文件传输

```bash
# 上传文件
python -m remote_cmd upload my-server ./local-file.txt /remote/path/

# 下载文件
python -m remote_cmd download my-server /remote/file.txt ./local/path/
```

#### 测试连接

```bash
python -m remote_cmd host test my-server
```

## 项目结构

```
remote-cmd-test/
├── remote_cmd/           # 主代码目录
│   ├── core/            # 核心功能模块
│   │   ├── ssh_client.py    # SSH 客户端实现
│   │   └── host_manager.py  # 主机管理器
│   ├── cli/             # 命令行接口
│   │   ├── main.py      # CLI 入口
│   │   └── commands.py  # 命令定义
│   └── utils/           # 工具函数
│       ├── config.py    # 配置管理
│       └── exceptions.py # 异常定义
├── tests/               # 测试目录
├── examples/            # 示例代码
├── .github/workflows/   # CI/CD 配置
├── config.example.yaml  # 配置文件示例
├── requirements.txt     # Python 依赖
├── README.md           # 项目说明
└── LICENSE             # 许可证
```

## 开发

### 运行测试

```bash
pytest tests/
```

### 代码格式化

```bash
black remote_cmd/
isort remote_cmd/
```

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 [MIT](LICENSE) 许可证。

## 作者

**Vae-Scrooge** - [GitHub Profile](https://github.com/Vae-Scrooge)

## 致谢

- [Paramiko](https://www.paramiko.org/) - Python SSH 库
- [Click](https://click.palletsprojects.com/) - Python 命令行工具库

---

⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！
