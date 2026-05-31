"""凭据提供链测试"""

import os

from remote_cmd.core.host import Host
from remote_cmd.service.credential_provider import (
    ChainCredentialProvider,
    EnvCredentialProvider,
)


class TestEnvCredentialProvider:
    """环境变量凭据提供者测试"""

    def test_get_password_from_env(self):
        """测试：从环境变量获取密码"""
        os.environ["TEST_CREDENTIAL"] = "env_password"
        try:
            provider = EnvCredentialProvider("TEST_CREDENTIAL")
            host = Host(name="srv", hostname="1", username="u")
            password = provider.get_password(host)
            assert password == "env_password"
        finally:
            del os.environ["TEST_CREDENTIAL"]

    def test_env_not_set_returns_none(self):
        """测试：环境变量未设置时返回 None"""
        provider = EnvCredentialProvider("NONEXISTENT_VAR_12345")
        host = Host(name="srv", hostname="1", username="u")
        assert provider.get_password(host) is None

    def test_env_empty_returns_empty(self):
        """测试：环境变量为空时返回空字符串"""
        os.environ["TEST_CREDENTIAL_EMPTY"] = ""
        try:
            provider = EnvCredentialProvider("TEST_CREDENTIAL_EMPTY")
            host = Host(name="srv", hostname="1", username="u")
            assert provider.get_password(host) == ""
        finally:
            del os.environ["TEST_CREDENTIAL_EMPTY"]


class TestChainCredentialProvider:
    """链式凭据提供者测试"""

    def test_chain_first_provider_wins(self):
        """测试：链中第一个返回非空值的提供者胜出"""
        chain = ChainCredentialProvider(
            [
                EnvCredentialProvider("FIRST_VAR"),
                EnvCredentialProvider("SECOND_VAR"),
            ]
        )

        os.environ["FIRST_VAR"] = "first"
        os.environ["SECOND_VAR"] = "second"
        try:
            host = Host(name="srv", hostname="1", username="u")
            assert chain.get_password(host) == "first"
        finally:
            del os.environ["FIRST_VAR"]
            del os.environ["SECOND_VAR"]

    def test_chain_falls_through(self):
        """测试：链中前面的提供者返回 None 时尝试下一个"""
        chain = ChainCredentialProvider(
            [
                EnvCredentialProvider("NONEXISTENT_1"),
                EnvCredentialProvider("EXISTENT_2"),
            ]
        )

        os.environ["EXISTENT_2"] = "fallback_password"
        try:
            host = Host(name="srv", hostname="1", username="u")
            assert chain.get_password(host) == "fallback_password"
        finally:
            del os.environ["EXISTENT_2"]

    def test_empty_chain_returns_none(self):
        """测试：空链返回 None"""
        chain = ChainCredentialProvider([])
        host = Host(name="srv", hostname="1", username="u")
        assert chain.get_password(host) is None

    def test_add_provider(self):
        """测试：动态添加提供者"""
        chain = ChainCredentialProvider([])
        chain.add_provider(EnvCredentialProvider("TEST_ADD_VAR"))

        os.environ["TEST_ADD_VAR"] = "added"
        try:
            host = Host(name="srv", hostname="1", username="u")
            assert chain.get_password(host) == "added"
        finally:
            del os.environ["TEST_ADD_VAR"]
