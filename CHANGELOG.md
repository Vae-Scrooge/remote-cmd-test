# 更新日志

所有 notable 的更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/).

## [1.0.0] - 2026-05-31

### Added
- 发布到 PyPI，支持 `pip install remote-cmd`
- 添加 PyPI 版本和下载量 badge
- README 添加英文简介，方便海外用户
- setup.py 添加 PyPI 下载链接和项目 URL

### Changed
- 安装方式优化：pip install 成为首选安装方式
- README 结构调整，更清晰的安装指引

## [Unreleased]

### Added
- 完善文档体系
  - 添加架构文档
  - 添加快速入门教程
  - 添加高级使用教程
  - 更新 API 文档
  - 更新故障排查指南
  - 添加安全策略文档

## [1.0.0] - 2024-01-15

### Added
- 初始版本发布
- ✅ SSH 连接管理（密码和密钥认证）
- ✅ 远程命令执行（同步/异步）
- ✅ 文件传输（SFTP 上传/下载）
- ✅ 主机管理系统（JSON 持久化）
- ✅ 标签分类系统
- ✅ 完整的 CLI 工具
- ✅ Python API
- ✅ 上下文管理器支持
- ✅ Sudo 命令执行
- ✅ 连接健康检查
- ✅ 配置管理（YAML/JSON）
- ✅ 完善的错误处理
- ✅ 日志系统
- ✅ 单元测试

### Core Features
- `SSHClient` - SSH 连接客户端
- `HostManager` - 主机管理器
- `ConnectionConfig` - 连接配置
- `CommandResult` - 命令执行结果
- `Host` - 主机配置数据类

### CLI Commands
- `host add` - 添加主机
- `host list` - 列出主机
- `host remove` - 删除主机
- `host test` - 测试连接
- `run` - 执行远程命令
- `upload` - 上传文件
- `download` - 下载文件

### Documentation
- README.md
- API.md
- CONTRIBUTING.md
- TROUBLESHOOTING.md
- LICENSE

---

## 版本说明

### 语义化版本规则

- **MAJOR** - 不兼容的 API 修改
- **MINOR** - 向下兼容的功能新增
- **PATCH** - 向下兼容的问题修复

### 版本标签说明

- `[Unreleased]` - 未发布的更改
- `Added` - 新增功能
- `Changed` - 变更
- `Deprecated` - 弃用
- `Removed` - 移除
- `Fixed` - 修复
- `Security` - 安全相关

---

**查看完整历史：** [GitHub Releases](https://github.com/Vae-Scrooge/remote-cmd-test/releases)
