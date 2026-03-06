"""
Webhook 处理单元测试
"""
import pytest
import json
import hmac
import hashlib
from unittest.mock import Mock, patch
from webhook.server import WebhookHandler


class TestWebhookHandler:
    """Webhook 处理器测试"""
    
    @pytest.fixture
    def handler(self):
        """创建测试处理器"""
        mock_db = Mock()
        mock_sync = Mock()
        return WebhookHandler(mock_db, mock_sync, encrypt_key='test-key')
    
    def test_verify_signature_success(self, handler):
        """测试签名验证成功"""
        timestamp = '1234567890'
        nonce = 'test-nonce'
        body = '{"test": "data"}'
        
        # 计算正确签名
        content = 'test-key' + timestamp + nonce + body
        signature = hmac.new(
            'test-key'.encode(),
            content.encode(),
            hashlib.sha256
        ).hexdigest()
        
        result = handler.verify_signature(signature, timestamp, nonce, body)
        assert result is True
    
    def test_verify_signature_fail(self, handler):
        """测试签名验证失败"""
        result = handler.verify_signature('wrong-sig', '123', 'nonce', '{}')
        assert result is False
    
    def test_handle_user_created_event(self, handler):
        """测试处理用户创建事件"""
        event_data = {
            'header': {
                'event_type': 'contact.user.created',
                'event_id': 'evt-001'
            },
            'event': {
                'user': {
                    'open_id': 'ou-new-user'
                }
            }
        }
        
        result = handler.handle_event(event_data)
        
        assert result['code'] == 0
        handler.sync_service.incremental_sync.assert_called_once_with([{
            'type': 'user',
            'id': 'ou-new-user',
            'action': 'create'
        }])
    
    def test_handle_user_updated_event(self, handler):
        """测试处理用户更新事件"""
        event_data = {
            'header': {
                'event_type': 'contact.user.updated',
                'event_id': 'evt-002'
            },
            'event': {
                'user': {
                    'open_id': 'ou-existing-user'
                }
            }
        }
        
        result = handler.handle_event(event_data)
        
        assert result['code'] == 0
        handler.sync_service.incremental_sync.assert_called_once_with([{
            'type': 'user',
            'id': 'ou-existing-user',
            'action': 'update'
        }])
    
    def test_handle_user_deleted_event(self, handler):
        """测试处理用户删除事件"""
        event_data = {
            'header': {
                'event_type': 'contact.user.deleted',
                'event_id': 'evt-003'
            },
            'event': {
                'user': {
                    'open_id': 'ou-deleted-user'
                }
            }
        }
        
        result = handler.handle_event(event_data)
        
        assert result['code'] == 0
        handler.sync_service.incremental_sync.assert_called_once_with([{
            'type': 'user',
            'id': 'ou-deleted-user',
            'action': 'delete'
        }])
    
    def test_handle_department_events(self, handler):
        """测试处理部门事件"""
        for event_type, action in [
            ('contact.department.created', 'create'),
            ('contact.department.updated', 'update'),
            ('contact.department.deleted', 'delete')
        ]:
            handler.sync_service.reset_mock()
            
            event_data = {
                'header': {
                    'event_type': event_type,
                    'event_id': f'evt-{action}'
                },
                'event': {
                    'department': {
                        'open_department_id': 'od-test-dept'
                    }
                }
            }
            
            result = handler.handle_event(event_data)
            
            assert result['code'] == 0
            handler.sync_service.incremental_sync.assert_called_once_with([{
                'type': 'department',
                'id': 'od-test-dept',
                'action': action
            }])
    
    def test_handle_unknown_event(self, handler):
        """测试处理未知事件类型"""
        event_data = {
            'header': {
                'event_type': 'unknown.event',
                'event_id': 'evt-unknown'
            }
        }
        
        result = handler.handle_event(event_data)
        
        assert result['code'] == 0
        assert '未处理' in result['msg']
