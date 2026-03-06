"""
API 集成测试
需要启动服务后测试
"""
import pytest
import requests
import json

# 测试配置
BASE_URL = 'http://localhost:8000'


@pytest.mark.integration
class TestAPIIntegration:
    """API 集成测试"""
    
    def test_health_endpoint(self):
        """测试健康检查接口"""
        response = requests.get(f'{BASE_URL}/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'timestamp' in data
    
    def test_departments_list_empty(self):
        """测试空部门列表"""
        response = requests.get(f'{BASE_URL}/api/departments')
        
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert 'data' in data
    
    def test_users_list_empty(self):
        """测试空用户列表"""
        response = requests.get(f'{BASE_URL}/api/users')
        
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
    
    def test_stats_endpoint(self):
        """测试统计接口"""
        response = requests.get(f'{BASE_URL}/api/stats')
        
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert 'departments' in data['data']
        assert 'users' in data['data']
    
    def test_search_short_keyword(self):
        """测试搜索关键词太短"""
        response = requests.get(f'{BASE_URL}/api/users/search?q=a')
        
        assert response.status_code == 400
        data = response.json()
        assert data['code'] == 400
    
    def test_get_nonexistent_user(self):
        """测试获取不存在的用户"""
        response = requests.get(f'{BASE_URL}/api/users/nonexistent-id')
        
        assert response.status_code == 404
        data = response.json()
        assert data['code'] == 404
    
    def test_get_nonexistent_department(self):
        """测试获取不存在的部门"""
        response = requests.get(f'{BASE_URL}/api/departments/nonexistent-id')
        
        assert response.status_code == 404
        data = response.json()
        assert data['code'] == 404


@pytest.mark.integration
class TestWebhookIntegration:
    """Webhook 集成测试"""
    
    WEBHOOK_URL = 'http://localhost:8001/webhook'
    
    def test_webhook_url_verification(self):
        """测试 Webhook URL 验证"""
        payload = {
            'type': 'url_verification',
            'challenge': 'test-challenge-123'
        }
        
        response = requests.post(
            self.WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['challenge'] == 'test-challenge-123'
    
    def test_webhook_invalid_signature(self):
        """测试无效签名"""
        payload = {'test': 'data'}
        
        response = requests.post(
            self.WEBHOOK_URL,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Lark-Signature': 'invalid-sig',
                'X-Lark-Request-Timestamp': '1234567890',
                'X-Lark-Request-Nonce': 'test-nonce'
            }
        )
        
        # 应该返回 401 或处理请求（如果没有配置加密密钥）
        assert response.status_code in [200, 401]
