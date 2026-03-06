#!/usr/bin/env python3
"""
Feishu Organization Sync Service
主入口文件
"""
import os
import sys
import argparse
import logging
from threading import Thread

from config import Config
from db.models import Database
from api.feishu_client import FeishuClient
from sync.sync_service import SyncService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_sync_service(config: Config, db: Database):
    """运行同步服务（定时任务）"""
    import time
    from datetime import datetime
    
    client = FeishuClient(
        app_id=config.feishu_app_id,
        app_secret=config.feishu_app_secret,
        domain=config.feishu_domain
    )
    
    service = SyncService(db, client)
    
    logger.info(f"启动定时同步服务，间隔: {config.sync_interval}秒")
    
    while True:
        try:
            logger.info(f"[{datetime.now()}] 开始定时同步...")
            result = service.full_sync()
            logger.info(f"同步完成: {result}")
        except Exception as e:
            logger.error(f"同步失败: {e}")
        
        time.sleep(config.sync_interval)


def main():
    parser = argparse.ArgumentParser(description='Feishu Organization Sync Service')
    parser.add_argument('--mode', choices=['api', 'webhook', 'sync', 'all'], default='all',
                       help='运行模式: api-仅API服务, webhook-仅Webhook服务, sync-仅同步服务, all-全部')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8000, help='监听端口')
    args = parser.parse_args()
    
    # 加载配置
    config = Config()
    
    # 初始化数据库
    db = Database(config.database_url)
    logger.info("数据库已初始化")
    
    threads = []
    
    # 启动 API 服务
    if args.mode in ['api', 'all']:
        from api.server import init_api, run_api_server
        init_api(db)
        
        api_thread = Thread(target=run_api_server, args=(args.host, args.port, False))
        api_thread.daemon = True
        api_thread.start()
        threads.append(api_thread)
        logger.info(f"API 服务已启动: http://{args.host}:{args.port}")
    
    # 启动 Webhook 服务
    if args.mode in ['webhook', 'all']:
        from webhook.server import init_webhook, run_webhook_server
        from api.feishu_client import FeishuClient
        from sync.sync_service import SyncService
        
        client = FeishuClient(
            app_id=config.feishu_app_id,
            app_secret=config.feishu_app_secret,
            domain=config.feishu_domain
        )
        service = SyncService(db, client)
        init_webhook(db, service, config.webhook_encrypt_key)
        
        webhook_port = args.port + 1 if args.mode == 'all' else args.port
        webhook_thread = Thread(target=run_webhook_server, args=(args.host, webhook_port, False))
        webhook_thread.daemon = True
        webhook_thread.start()
        threads.append(webhook_thread)
        logger.info(f"Webhook 服务已启动: http://{args.host}:{webhook_port}/webhook")
    
    # 启动同步服务
    if args.mode in ['sync', 'all']:
        sync_thread = Thread(target=run_sync_service, args=(config, db))
        sync_thread.daemon = True
        sync_thread.start()
        threads.append(sync_thread)
    
    logger.info("所有服务已启动，按 Ctrl+C 停止")
    
    # 保持主线程运行
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("正在停止服务...")
        sys.exit(0)


if __name__ == '__main__':
    main()
