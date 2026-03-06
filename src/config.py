"""
配置管理模块
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class FeishuConfig:
    """飞书配置"""
    app_id: str
    app_secret: str
    domain: str = "https://open.feishu.cn"
    encrypt_key: Optional[str] = None
    verification_token: Optional[str] = None


@dataclass
class DatabaseConfig:
    """数据库配置"""
    path: str = "/app/data/org_sync.db"


@dataclass
class SyncConfig:
    """同步配置"""
    full_sync_interval: int = 3600  # 全量同步间隔（秒）
    batch_size: int = 100  # 批量处理大小


@dataclass
class ServerConfig:
    """服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class Config:
    """全局配置"""
    
    def __init__(self):
        self.feishu = FeishuConfig(
            app_id=os.getenv("FEISHU_APP_ID", ""),
            app_secret=os.getenv("FEISHU_APP_SECRET", ""),
            domain=os.getenv("FEISHU_DOMAIN", "https://open.feishu.cn"),
            encrypt_key=os.getenv("FEISHU_ENCRYPT_KEY"),
            verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN")
        )
        self.database = DatabaseConfig(
            path=os.getenv("DB_PATH", "/app/data/org_sync.db")
        )
        self.sync = SyncConfig(
            full_sync_interval=int(os.getenv("FULL_SYNC_INTERVAL", "3600")),
            batch_size=int(os.getenv("BATCH_SIZE", "100"))
        )
        self.server = ServerConfig(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8000")),
            debug=os.getenv("DEBUG", "false").lower() == "true"
        )
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        return cls()


# 全局配置实例
config = Config.from_env()
