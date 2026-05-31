"""
命令行接口模块

提供完整的命令行工具，用于管理远程主机和执行 SSH 操作。
基于 Click 框架构建，支持丰富的命令和选项。

主要命令：
- host: 主机管理命令组
  - add: 添加新主机
  - list: 列出所有主机
  - remove: 移除主机
  - test: 测试主机连接
- run: 在远程主机上执行命令
- upload: 上传文件到远程主机
- download: 从远程主机下载文件

Author: Vae-Scrooge
"""

import click
import os
from typing import Optional

from remote_cmd.core.host_manager import HostManager, Host
from remote_cmd.core.ssh_client import SSHClient
from remote_cmd.utils.config import load_config, get_default_config_path

# ============================================================================
# CLI 主入口
# ============================================================================


@click.group()
@click.version_option(version="1.0.0", prog_name="remote-cmd")
@click.option("--config", "-c", type=click.Path(), help="配置文件路径")
@click.option("--verbose", "-v", is_flag=True, help="启用详细输出模式")
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """
    Remote CMD - SSH 远程服务器管理工具

    一个功能强大的命令行工具，用于管理远程主机配置、
    执行命令和传输文件。

    快速开始：
        # 添加主机
        remote-cmd host add my-server 192.168.1.100 admin -k ~/.ssh/id_rsa

        # 列出所有主机
        remote-cmd host list

        # 执行远程命令
        remote-cmd run my-server "ls -la"

        # 上传文件
        remote-cmd upload my-server ./local.txt /remote/path.txt
    """
    # 初始化上下文对象
    ctx.ensure_object(dict)

    # 加载配置文件
    config_path = config or get_default_config_path()
    ctx.obj["config"] = load_config(config_path)
    ctx.obj["verbose"] = verbose

    # 详细模式下显示配置信息
    if verbose:
        click.echo(f"使用配置文件: {config_path}")


# ============================================================================
# 主机管理命令组
# ============================================================================


@cli.group()
def host():
    """
    主机管理命令组

    用于添加、删除、列出、查看和测试远程主机连接。

    可用命令：
        add     添加新主机
        list    列出所有主机
        show    查看主机详情
        remove  移除主机
        test    测试主机连接
    """
    pass


@host.command("add")
@click.argument("name", required=True)
@click.argument("hostname", required=True)
@click.argument("username", required=True)
@click.option("--port", "-p", default=22, help="SSH 端口号（默认：22）")
@click.option(
    "--password",
    "-P",
    default=None,
    help="登录密码（不推荐直接在命令行输入，建议使用 REMOTE_CMD_PASSWORD 环境变量或交互式输入）",
)
@click.option("--key", "-k", help="SSH 私钥文件路径")
@click.option("--tag", "-t", multiple=True, help="主机标签（可多次指定）")
@click.option("--description", "-d", default="", help="主机描述")
@click.pass_context
def host_add(
    ctx,
    name: str,
    hostname: str,
    username: str,
    port: int,
    password: Optional[str],
    key: Optional[str],
    tag: tuple,
    description: str,
):
    """
    添加新主机

    NAME: 主机名称（唯一标识符）
    HOSTNAME: 主机地址（IP 或域名）
    USERNAME: SSH 登录用户名

    示例：
        # 使用 SSH 密钥认证（推荐）
        remote-cmd host add server1 192.168.1.100 admin -k ~/.ssh/id_rsa

        # 使用密码认证
        REMOTE_CMD_PASSWORD=mypassword remote-cmd host add server1 192.168.1.100 admin

        # 添加标签
        remote-cmd host add server2 192.168.1.102 admin -k ~/.ssh/id_rsa -t web -t production
    """
    config_file = ctx.obj["config"].get("hosts_file", "hosts.json")
    manager = HostManager(config_file)

    # 获取密码：优先级  REMOTE_CMD_PASSWORD > --password > 交互式输入
    resolved_password = os.environ.get("REMOTE_CMD_PASSWORD") or password
    if not resolved_password and not key:
        resolved_password = click.prompt(
            "SSH 密码", hide_input=True, default="", show_default=False
        )
    elif password and not os.environ.get("REMOTE_CMD_PASSWORD"):
        click.echo(
            click.style(
                "⚠ 警告: 在命令行参数中传递密码不安全，建议使用 REMOTE_CMD_PASSWORD 环境变量",
                fg="yellow",
            ),
            err=True,
        )

    # 创建主机配置对象
    host = Host(
        name=name,
        hostname=hostname,
        username=username,
        port=port,
        password=resolved_password or password,
        key_filename=key,
        tags=list(tag),
        description=description,
    )

    try:
        # 添加主机并保存配置
        manager.add_host(host)
        manager.save_to_file(config_file)

        click.echo(f"✓ 主机 '{name}' 添加成功")

    except ValueError as e:
        click.echo(f"✗ 错误: {e}", err=True)
        ctx.exit(1)


@host.command("list")
@click.option("--tag", "-t", help="按标签筛选主机")
@click.pass_context
def host_list(ctx, tag: Optional[str]):
    """
    列出所有主机

    显示所有已配置的主机信息，可选按标签筛选。

    示例：
        # 列出所有主机
        remote-cmd host list

        # 列出特定标签的主机
        remote-cmd host list -t production
    """
    config_file = ctx.obj["config"].get("hosts_file", "hosts.json")
    manager = HostManager(config_file)

    # 获取主机列表
    hosts = manager.list_hosts(tag=tag)

    if not hosts:
        if tag:
            click.echo(f"没有找到标签为 '{tag}' 的主机")
        else:
            click.echo("没有配置任何主机")
        return

    # 格式化输出表头
    click.echo(f"\n{'名称':<20} {'主机地址':<25} {'用户名':<15} {'标签':<20}")
    click.echo("-" * 80)

    # 输出主机信息
    for host in hosts:
        tags_str = ", ".join(host.tags) if host.tags else "-"
        click.echo(
            f"{host.name:<20} {host.hostname:<25} {host.username:<15} {tags_str:<20}"
        )

    click.echo()


@host.command("remove")
@click.argument("name", required=True)
@click.confirmation_option(prompt="确定要移除这个主机吗？")
@click.pass_context
def host_remove(ctx, name: str):
    """
    移除主机

    NAME: 要移除的主机名称

    示例：
        remote-cmd host remove old-server
    """
    config_file = ctx.obj["config"].get("hosts_file", "hosts.json")
    manager = HostManager(config_file)

    try:
        manager.remove_host(name)
        manager.save_to_file(config_file)

        click.echo(f"✓ 主机 '{name}' 已移除")

    except KeyError as e:
        click.echo(f"✗ 错误: {e}", err=True)
        ctx.exit(1)


@host.command("show")
@click.argument("name", required=True)
@click.pass_context
def host_show(ctx, name: str):
    """
    显示主机详细信息

    NAME: 主机名称

    示例：
        remote-cmd host show web-server
    """
    config_file = ctx.obj["config"].get("hosts_file", "hosts.json")
    manager = HostManager(config_file)

    try:
        host = manager.get_host(name)
        click.echo(f"\n{'=' * 50}")
        click.echo(f"  主机详情: {host.name}")
        click.echo(f"{'=' * 50}")
        click.echo(f"  名称:      {host.name}")
        click.echo(f"  主机地址:  {host.hostname}")
        click.echo(f"  用户名:    {host.username}")
        click.echo(f"  端口:      {host.port}")
        click.echo(
            f"  认证方式:  {'密码' if host.password else 'SSH 密钥' if host.key_filename else 'SSH Agent'}"
        )
        if host.key_filename:
            click.echo(f"  密钥路径:  {host.key_filename}")
        tags_str = ", ".join(host.tags) if host.tags else "-"
        click.echo(f"  标签:      {tags_str}")
        click.echo(f"  描述:      {host.description or '-'}")
        click.echo(f"{'=' * 50}\n")
    except KeyError as e:
        click.echo(f"✗ 错误: {e}", err=True)
        ctx.exit(1)


@host.command("test")
@click.argument("name", required=True)
@click.pass_context
def host_test(ctx, name: str):
    """
    测试主机连接

    NAME: 要测试的主机名称

    示例：
        remote-cmd host test web-server
    """
    config_file = ctx.obj["config"].get("hosts_file", "hosts.json")
    manager = HostManager(config_file)

    click.echo(f"正在测试 '{name}' 的连接...")

    if manager.test_connection(name):
        click.echo(f"✓ 主机 '{name}' 连接成功")
    else:
        click.echo(f"✗ 主机 '{name}' 连接失败", err=True)
        ctx.exit(1)


# ============================================================================
# 远程操作命令
# ============================================================================


@cli.command()
@click.argument("host_name", required=True)
@click.argument("command", required=True)
@click.pass_context
def run(ctx, host_name: str, command: str):
    """
    在远程主机上执行命令

    HOST_NAME: 主机名称
    COMMAND: 要执行的命令

    示例：
        remote-cmd run web-server "ls -la"
        remote-cmd run db-server "uptime"
    """
    config_file = ctx.obj["config"].get("hosts_file", "hosts.json")
    manager = HostManager(config_file)

    try:
        with manager.connect_to_host(host_name) as client:
            result = client.execute(command)

            # 输出命令结果
            if result.stdout:
                click.echo(result.stdout)

            if result.stderr:
                click.echo(result.stderr, err=True)

            # 使用命令的退出码
            ctx.exit(result.exit_code)

    except Exception as e:
        click.echo(f"✗ 错误: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("host_name", required=True)
@click.argument("local_path", required=True)
@click.argument("remote_path", required=True)
@click.pass_context
def upload(ctx, host_name: str, local_path: str, remote_path: str):
    """
    上传文件到远程主机

    HOST_NAME: 主机名称
    LOCAL_PATH: 本地文件路径
    REMOTE_PATH: 远程目标路径

    示例：
        remote-cmd upload web-server ./script.sh /tmp/script.sh
    """
    config_file = ctx.obj["config"].get("hosts_file", "hosts.json")
    manager = HostManager(config_file)

    try:
        with manager.connect_to_host(host_name) as client:
            client.upload_file(local_path, remote_path)
            click.echo(f"✓ 上传成功: {local_path} -> {host_name}:{remote_path}")

    except Exception as e:
        click.echo(f"✗ 错误: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("host_name", required=True)
@click.argument("remote_path", required=True)
@click.argument("local_path", required=True)
@click.pass_context
def download(ctx, host_name: str, remote_path: str, local_path: str):
    """
    从远程主机下载文件

    HOST_NAME: 主机名称
    REMOTE_PATH: 远程文件路径
    LOCAL_PATH: 本地目标路径

    示例：
        remote-cmd download web-server /var/log/syslog ./logs/syslog
    """
    config_file = ctx.obj["config"].get("hosts_file", "hosts.json")
    manager = HostManager(config_file)

    try:
        with manager.connect_to_host(host_name) as client:
            client.download_file(remote_path, local_path)
            click.echo(f"✓ 下载成功: {host_name}:{remote_path} -> {local_path}")

    except Exception as e:
        click.echo(f"✗ 错误: {e}", err=True)
        ctx.exit(1)


# ============================================================================
# 程序入口
# ============================================================================


def main():
    """
    CLI 程序入口点

    由 setup.py 的 console_scripts 配置调用。
    也可以直接运行此模块：python -m remote_cmd.cli.main
    """
    cli()


if __name__ == "__main__":
    main()
