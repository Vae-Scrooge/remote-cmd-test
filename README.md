# Remote CMD - SSH 远程服务器管理工具

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/remote-cmd)](https://pypi.org/project/remote-cmd/)
[![PyPI downloads](https://img.shields.io/pypi/dm/remote-cmd)](https://pypi.org/project/remote-cmd/)
[![Code Style](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![Build Status](https://github.com/Vae-Scrooge/remote-cmd-test/workflows/CI/badge.svg)](https://github.com/Vae-Scrooge/remote-cmd-test/actions)
[![Documentation](https://img.shields.io/badge/docs-complete-brightgreen)](./docs)

**A lightweight Python SSH remote server management tool for developers and sysadmins.**

```bash
pip install remote-cmd
```

[快速开始](#快速开始) | [安装指南](#安装指南) | [使用文档](#详细使用说明) | [API 文档](./docs/API.md) | [开发指南](./docs/DEVELOPMENT.md) | [故障排查](./docs/TROUBLESHOOTING.md)

</div>

---

Remote CMD is a Python-based SSH tool that helps you manage remote servers from the command line or your own Python scripts. Built on Paramiko, it supports password and SSH key auth, remote command execution, file transfer (SFTP), multi-host tagging, and batch operations — all without needing Ansible or other heavy orchestration tools.

```python
from remote_cmd.core.ssh_client import SSHClient, ConnectionConfig

with SSHClient(ConnectionConfig(hostname="192.168.1.100", username="ubuntu", password="yourpassword")) as client:
    result = client.execute("uptime")
    print(result.stdout)
```

---

## 目录

- [项目简介](#项目简介)
- [特性](#特性)
- [架构说明](#架构说明)
- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [详细使用说明](#详细使用说明)
- [配置说明](#配置说明)
- [示例场景](#示例场景)
- [开发指南](./docs/DEVELOPMENT.md)
- [故障排查](./docs/TROUBLESHOOTING.md)
- [更新日志](./CHANGELOG.md)
- [许可证](#许可证)

---

## 项目简介

Remote CMD 是一个基于 Python 3.8+ 开发的 SSH 远程服务器管理工具。它提供了简洁的命令行界面和强大的 Python API，帮助开发者和系统管理员更高效地管理远程服务器。

### 为什么选择 Remote CMD？

- **简单易用**：直观的命令行设计，几分钟即可上手
- **功能完整**：支持 SSH 连接、命令执行、文件传输、主机管理等核心功能
- **安全可靠**：支持密码和 SSH Key 两种认证方式
- **扩展性强**：清晰的模块化设计，易于扩展和二次开发
- **文档完善**：详细的文档和丰富的示例，降低学习成本
- **安装便捷**：一行命令 `pip install remote-cmd` 即可安装

---

## 特性

### 核心功能

| 功能 | 描述 | 状态 |
|------|------|------|
| 🔐 **SSH 连接管理** | 支持密码和 SSH Key 认证 | ✅ 已完成 |
| 🖥️ **远程命令执行** | 在远程服务器上执行命令并获取输出 | ✅ 已完成 |
| 📁 **文件传输** | 支持上传和下载文件 | ✅ 已完成 |
| 🗂️ **主机管理** | 统一管理多台服务器配置 | ✅ 已完成 |
| 🏷️ **标签系统** | 为主机打标签，便于分类管理 | ✅ 已完成 |
| 🔍 **连接测试** | 快速检测服务器连通性 | ✅ 已完成 |
| 📊 **批量操作** | 在多台服务器上执行相同操作 | ✅ 已完成 |
| 🔒 **Sudo 支持** | 执行需要管理员权限的命令 | ✅ 已完成 |

### 技术特性

- **类型安全**：完整的类型注解支持
- **异常处理**：完善的错误处理机制
- **日志记录**：详细的操作日志
- **单元测试**：全面的测试覆盖
- **CI/CD**：自动化测试和部署

---

## 架构说明

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   CLI 命令    │  │  Python API  │  │  配置文件     │      │
│  │   remote-cmd  │  │   程序化调用  │  │  YAML/JSON   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                       应用层                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 HostManager 主机管理器                  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐│  │
│  │  │   添加主机    │  │   删除主机    │  │   查询主机    ││  │
│  │  │   标签管理    │  │   批量操作    │  │   连接测试    ││  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘│  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                       核心层                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  SSHClient SSH 客户端                   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐│  │
│  │  │   建立连接    │  │   执行命令    │  │   文件传输    ││  │
│  │  │   认证管理    │  │   获取输出    │  │   SFTP 操作  ││  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘│  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                      网络层                                   │
│                Paramiko (SSH 协议实现)                        │
└─────────────────────────────────────────────────────────────┘
```

### 模块说明

#### 1. Core 模块 (`remote_cmd/core/`)

**SSHClient** - SSH 连接客户端
- 负责建立和管理 SSH 连接
- 提供命令执行接口
- 支持文件传输（SFTP）
- 使用上下文管理器确保资源释放

**HostManager** - 主机管理器
- 管理主机配置信息
- 提供增删改查接口
- 支持标签分类
- 数据持久化（JSON 格式）

#### 2. CLI 模块 (`remote_cmd/cli/`)

**Main** - 命令行入口
- 基于 Click 框架实现
- 提供友好的命令行界面
- 支持子命令和参数解析
- 错误处理和帮助信息

#### 3. Utils 模块 (`remote_cmd/utils/`)

**Config** - 配置管理
- 加载和保存配置文件
- 支持 YAML 和 JSON 格式
- 默认配置管理

**Exceptions** - 异常定义
- 自定义异常层次结构
- 清晰的错误分类
- 便于错误处理

---

## 安装指南

### 环境要求

- Python 3.8 或更高版本
- pip 包管理器
- （可选）虚拟环境工具

### 安装步骤

#### 方式 1：从 PyPI 安装（推荐）

```bash
pip install remote-cmd
```

#### 方式 2：从源代码安装（开发者）

```bash
git clone https://github.com/Vae-Scrooge/remote-cmd-test.git
cd remote-cmd-test
pip install -e .
```

#### 方式 3：开发模式安装

```bash
pip install -e ".[dev]"
```

### 验证安装

```bash
remote-cmd --version
```

---

## 快速开始

### 5 分钟上手

```bash
# 1. 添加第一台服务器
python -m remote_cmd host add my-server 192.168.1.100 ubuntu --password yourpassword

# 2. 测试连接
python -m remote_cmd host test my-server

# 3. 执行命令
python -m remote_cmd run my-server "ls -la"

# 4. 查看所有主机
python -m remote_cmd host list
```

### 第一个 Python 脚本

```python
from remote_cmd.core.ssh_client import SSHClient, ConnectionConfig

# 配置连接信息
config = ConnectionConfig(
    hostname="192.168.1.100",
    username="ubuntu",
    password="yourpassword",
    port=22
)

# 建立连接并执行命令
with SSHClient(config) as client:
    result = client.execute("uptime")
    print(f"服务器运行时间: {result.stdout}")
```

---

## 详细使用说明

### 主机管理

#### 添加主机

```bash
# 使用密码认证
python -m remote_cmd host add <名称> <主机名> <用户名> --password <密码>

# 使用 SSH Key
python -m remote_cmd host add <名称> <主机名> <用户名> --key <密钥路径>

# 添加标签
python -m remote_cmd host add web-server 192.168.1.10 ubuntu \
    --key ~/.ssh/id_rsa \
    --tag production \
    --tag web \
    --description "Production web server"
```

**参数说明：**
- `name` - 主机别名（唯一标识）
- `hostname` - 服务器地址（IP 或域名）
- `username` - SSH 用户名
- `--port` - SSH 端口（默认 22）
- `--password` - 密码认证
- `--key` - SSH 私钥路径
- `--tag` - 标签（可多个）
- `--description` - 描述信息

#### 查看主机

```bash
# 列出所有主机
python -m remote_cmd host list

# 按标签筛选
python -m remote_cmd host list --tag production

# 查看详细信息（未来版本）
python -m remote_cmd host show my-server
```

#### 删除主机

```bash
python -m remote_cmd host remove my-server
```

**注意：** 删除前会要求确认。

#### 测试连接

```bash
# 测试单个主机
python -m remote_cmd host test my-server

# 测试所有主机（通过脚本实现，见示例）
```

### 命令执行

#### 基本命令执行

```bash
python -m remote_cmd run <主机名> "<命令>"

# 示例
python -m remote_cmd run my-server "ls -la /var/www"
python -m remote_cmd run my-server "systemctl status nginx"
python -m remote_cmd run my-server "df -h"
```

#### 执行多行命令

```bash
python -m remote_cmd run my-server "cd /app && git pull && systemctl restart app"
```

#### 使用 Sudo

```bash
# 使用密码
python -m remote_cmd run my-server "sudo systemctl restart nginx"
# 系统会提示输入 sudo 密码

# 或者在 Python 中
result = client.execute_sudo("systemctl restart nginx", password="sudopass")
```

### 文件传输

#### 上传文件

```bash
python -m remote_cmd upload <主机名> <本地路径> <远程路径>

# 示例
python -m remote_cmd upload my-server ./deploy.sh /tmp/deploy.sh
python -m remote_cmd upload my-server ./config/nginx.conf /etc/nginx/nginx.conf
```

#### 下载文件

```bash
python -m remote_cmd download <主机名> <远程路径> <本地路径>

# 示例
python -m remote_cmd download my-server /var/log/nginx/error.log ./logs/
python -m remote_cmd download my-server /etc/nginx/nginx.conf ./backup/
```

#### Python API 示例

```python
with SSHClient(config) as client:
    # 上传文件
    client.upload_file("./local.txt", "/remote/path/file.txt")
    
    # 下载文件
    client.download_file("/remote/path/file.txt", "./local.txt")
    
    # 列出远程目录
    entries = client.list_remote_directory("/var/www")
    for entry in entries:
        print(f"{entry['name']}: {entry['size']} bytes")
```

### 批量操作

```python
from remote_cmd.core.host_manager import HostManager

manager = HostManager("hosts.json")

# 在所有生产环境服务器上执行命令
for host in manager.list_hosts(tag="production"):
    print(f"\n正在处理 {host.name}...")
    
    try:
        with manager.connect_to_host(host.name) as client:
            # 更新系统
            result = client.execute_sudo("apt update && apt upgrade -y", 
                                       password="sudopassword")
            
            if result.success:
                print(f"✓ {host.name} 更新成功")
            else:
                print(f"✗ {host.name} 更新失败: {result.stderr}")
    except Exception as e:
        print(f"✗ {host.name} 连接失败: {e}")
```

---

## 配置说明

### 配置文件位置

Remote CMD 按以下顺序查找配置文件：

1. 当前目录：`./config.yaml` 或 `./config.json`
2. 用户目录：`~/.remote_cmd/config.yaml`
3. 使用默认配置

### 配置选项

```yaml
# config.yaml 示例

# 主机配置文件路径
hosts_file: hosts.json

# 默认 SSH 设置
default_ssh_port: 22
default_timeout: 30

# 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level: INFO

# 日志文件路径（可选）
# log_file: logs/remote_cmd.log

# SSH 设置
ssh:
  # 是否严格检查主机密钥
  strict_host_key_checking: false
  
  # 压缩传输
  compress: true
  
  # 连接重试次数
  retry_count: 3
  
  # 重试间隔（秒）
  retry_delay: 5
```

### 环境变量

```bash
# 配置文件路径
export REMOTE_CMD_CONFIG=/path/to/config.yaml

# 主机文件路径
export REMOTE_CMD_HOSTS=/path/to/hosts.json

# 日志级别
export REMOTE_CMD_LOG_LEVEL=DEBUG
```

---

## 示例场景

### 场景 1：自动化部署

```python
#!/usr/bin/env python3
"""自动化部署脚本"""

from remote_cmd.core.host_manager import HostManager
import sys

def deploy(host_name):
    """部署应用到指定服务器"""
    manager = HostManager()
    
    with manager.connect_to_host(host_name) as client:
        print(f"🚀 开始部署到 {host_name}...")
        
        # 1. 上传代码
        print("📤 上传代码...")
        client.upload_file("./app.tar.gz", "/tmp/app.tar.gz")
        
        # 2. 解压并部署
        print("📦 部署应用...")
        commands = [
            "cd /var/www && tar -xzf /tmp/app.tar.gz",
            "cd /var/www/app && pip install -r requirements.txt",
            "sudo systemctl restart app"
        ]
        
        for cmd in commands:
            result = client.execute_sudo(cmd, password="sudopass")
            if not result.success:
                print(f"❌ 部署失败: {result.stderr}")
                sys.exit(1)
        
        print("✅ 部署完成！")

if __name__ == "__main__":
    deploy("production-server")
```

### 场景 2：日志收集

```python
#!/usr/bin/env python3
"""日志收集脚本"""

from remote_cmd.core.host_manager import HostManager
from pathlib import Path
from datetime import datetime

def collect_logs():
    """从所有服务器收集日志"""
    manager = HostManager("hosts.json")
    
    log_dir = Path("logs") / datetime.now().strftime("%Y%m%d")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    for host in manager.list_hosts(tag="web"):
        print(f"📥 从 {host.name} 收集日志...")
        
        try:
            with manager.connect_to_host(host.name) as client:
                remote_log = "/var/log/nginx/access.log"
                local_log = log_dir / f"{host.name}_access.log"
                
                client.download_file(remote_log, str(local_log))
                print(f"  ✅ 已保存到 {local_log}")
        except Exception as e:
            print(f"  ❌ 失败: {e}")

if __name__ == "__main__":
    collect_logs()
```

### 场景 3：系统监控

```python
#!/usr/bin/env python3
"""系统状态检查脚本"""

from remote_cmd.core.host_manager import HostManager
import json

def check_system_status():
    """检查所有服务器系统状态"""
    manager = HostManager("hosts.json")
    
    reports = []
    
    for host in manager.list_hosts():
        print(f"🔍 检查 {host.name}...")
        
        try:
            with manager.connect_to_host(host.name) as client:
                # 检查磁盘空间
                disk_result = client.execute("df -h / | tail -1")
                disk_usage = disk_result.stdout.split()[4]
                
                # 检查内存
                mem_result = client.execute("free -h | grep Mem")
                mem_info = mem_result.stdout.split()
                
                # 检查负载
                load_result = client.execute("uptime | awk -F'load average:' '{print $2}'")
                load = load_result.stdout.strip()
                
                report = {
                    "host": host.name,
                    "disk_usage": disk_usage,
                    "memory_used": mem_info[2],
                    "memory_total": mem_info[1],
                    "load_average": load,
                    "status": "healthy"
                }
                
                # 检查告警
                if int(disk_usage.replace('%', '')) > 80:
                    report["status"] = "warning"
                    print(f"  ⚠️  磁盘使用率高: {disk_usage}")
                else:
                    print(f"  ✅ 状态正常")
                
                reports.append(report)
                
        except Exception as e:
            print(f"  ❌ 检查失败: {e}")
            reports.append({
                "host": host.name,
                "status": "error",
                "error": str(e)
            })
    
    # 保存报告
    with open("system_report.json", "w") as f:
        json.dump(reports, f, indent=2)
    
    print(f"\n📊 报告已保存到 system_report.json")

if __name__ == "__main__":
    check_system_status()
```

---

## 文档索引

- **[API 文档](./docs/API.md)** - 详细的 API 参考
- **[开发指南](./docs/DEVELOPMENT.md)** - 如何参与开发
- **[贡献指南](./CONTRIBUTING.md)** - 如何贡献代码
- **[故障排查](./docs/TROUBLESHOOTING.md)** - 常见问题解答
- **[更新日志](./CHANGELOG.md)** - 版本更新记录

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

---

## 作者

**Vae-Scrooge**

- GitHub: [@Vae-Scrooge](https://github.com/Vae-Scrooge)
- 项目主页: https://github.com/Vae-Scrooge/remote-cmd-test
- PyPI: https://pypi.org/project/remote-cmd/

---

## 致谢

感谢以下开源项目：

- [Paramiko](https://www.paramiko.org/) - Python SSH 库
- [Click](https://click.palletsprojects.com/) - Python 命令行框架
- [PyYAML](https://pyyaml.org/) - YAML 解析库

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**

[回到顶部](#remote-cmd---ssh-远程服务器管理工具)

</div>
