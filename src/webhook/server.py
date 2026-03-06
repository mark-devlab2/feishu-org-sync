"""
Webhook 接收服务
处理飞书组织架构变更事件
"""
import json
import hmac
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any
from flask import Flask, request, jsonify
from functools import wraps

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db.models import Database, SyncLog
from sync.sync_service import SyncService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class WebhookHandler:
    """Webhook 处理器"""
    
    def __init__(self, db: Database, sync_service: SyncService, encrypt_key: str = None):
        self.db = db
        self.sync_service = sync_service
        self.encrypt_key = encrypt_key
    
    def verify_signature(self, signature: str, timestamp: str, nonce: str, body: str) -> bool:
        """验证飞书请求签名"""
        if not self.encrypt_key:
            logger.warning("未配置加密密钥，跳过签名验证")
            return True
        
        # 飞书签名算法：sha256(encrypt_key + timestamp + nonce + body)
        content = self.encrypt_key + timestamp + nonce + body
        computed = hmac.new(
            self.encrypt_key.encode(),
            content.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(computed, signature)
    
    def handle_event(self, event_data: Dict[str, Any]) -> Dict:
        """处理飞书事件"""
        event_type = event_data.get('header', {}).get('event_type')
        event_id = event_data.get('header', {}).get('event_id')
        
        logger.info(f"收到事件: {event_type}, ID: {event_id}")
        
        # 根据事件类型处理
        handlers = {
            'contact.user.created': self._handle_user_created,
            'contact.user.updated': self._handle_user_updated,
            'contact.user.deleted': self._handle_user_deleted,
            'contact.department.created': self._handle_dept_created,
            'contact.department.updated': self._handle_dept_updated,
            'contact.department.deleted': self._handle_dept_deleted,
        }
        
        handler = handlers.get(event_type)
        if handler:
            try:
                return handler(event_data)
            except Exception as e:
                logger.error(f"处理事件 {event_type} 失败: {e}")
                return {'code': 1, 'msg': f'处理失败: {str(e)}'}
        else:
            logger.warning(f"未知事件类型: {event_type}")
            return {'code': 0, 'msg': '事件已接收但未处理'}
    
    def _handle_user_created(self, event_data: Dict) -> Dict:
        """处理用户创建事件"""
        user_id = event_data.get('event', {}).get('user', {}).get('open_id')
        logger.info(f"用户创建事件: {user_id}")
        
        # 触发增量同步
        self.sync_service.incremental_sync([{
            'type': 'user',
            'id': user_id,
            'action': 'create'
        }])
        
        return {'code': 0, 'msg': 'success'}
    
    def _handle_user_updated(self, event_data: Dict) -> Dict:
        """处理用户更新事件"""
        user_id = event_data.get('event', {}).get('user', {}).get('open_id')
        logger.info(f"用户更新事件: {user_id}")
        
        self.sync_service.incremental_sync([{
            'type': 'user',
            'id': user_id,
            'action': 'update'
        }])
        
        return {'code': 0, 'msg': 'success'}
    
    def _handle_user_deleted(self, event_data: Dict) -> Dict:
        """处理用户删除事件"""
        user_id = event_data.get('event', {}).get('user', {}).get('open_id')
        logger.info(f"用户删除事件: {user_id}")
        
        self.sync_service.incremental_sync([{
            'type': 'user',
            'id': user_id,
            'action': 'delete'
        }])
        
        return {'code': 0, 'msg': 'success'}
    
    def _handle_dept_created(self, event_data: Dict) -> Dict:
        """处理部门创建事件"""
        dept_id = event_data.get('event', {}).get('department', {}).get('open_department_id')
        logger.info(f"部门创建事件: {dept_id}")
        
        self.sync_service.incremental_sync([{
            'type': 'department',
            'id': dept_id,
            'action': 'create'
        }])
        
        return {'code': 0, 'msg': 'success'}
    
    def _handle_dept_updated(self, event_data: Dict) -> Dict:
        """处理部门更新事件"""
        dept_id = event_data.get('event', {}).get('department', {}).get('open_department_id')
        logger.info(f"部门更新事件: {dept_id}")
        
        self.sync_service.incremental_sync([{
            'type': 'department',
            'id': dept_id,
            'action': 'update'
        }])
        
        return {'code': 0, 'msg': 'success'}
    
    def _handle_dept_deleted(self, event_data: Dict) -> Dict:
        """处理部门删除事件"""
        dept_id = event_data.get('event', {}).get('department', {}).get('open_department_id')
        logger.info(f"部门删除事件: {dept_id}")
        
        self.sync_service.incremental_sync([{
            'type': 'department',
            'id': dept_id,
            'action': 'delete'
        }])
        
        return {'code': 0, 'msg': 'success'}


# 全局处理器实例
webhook_handler = None

def init_webhook(db: Database, sync_service: SyncService, encrypt_key: str = None):
    """初始化 Webhook 处理器"""
    global webhook_handler
    webhook_handler = WebhookHandler(db, sync_service, encrypt_key)


@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook 接收端点"""
    if webhook_handler is None:
        return jsonify({'code': 1, 'msg': 'Webhook 未初始化'}), 500
    
    # 获取请求数据
    body = request.get_data(as_text=True)
    data = request.get_json()
    
    # 获取签名信息
    signature = request.headers.get('X-Lark-Signature')
    timestamp = request.headers.get('X-Lark-Request-Timestamp')
    nonce = request.headers.get('X-Lark-Request-Nonce')
    
    # 验证签名
    if signature and timestamp and nonce:
        if not webhook_handler.verify_signature(signature, timestamp, nonce, body):
            logger.warning("签名验证失败")
            return jsonify({'code': 1, 'msg': '签名验证失败'}), 401
    
    # 处理 URL 验证（飞书首次配置时会发送验证请求）
    if data.get('type') == 'url_verification':
        challenge = data.get('challenge')
        logger.info(f"URL 验证请求: {challenge}")
        return jsonify({'challenge': challenge})
    
    # 处理事件
    result = webhook_handler.handle_event(data)
    return jsonify(result)


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat()
    })


def run_webhook_server(host='0.0.0.0', port=8000, debug=False):
    """运行 Webhook 服务器"""
    logger.info(f"启动 Webhook 服务器: {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_webhook_server()
