"""
飞书 API 客户端单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from api.feishu_client import FeishuClient


class TestFeishuClient:
    """飞书客户端测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return FeishuClient(
            app_id='test-app-id',
            app_secret='test-app-secret'
        )
    
    @patch('api.feishu_client.requests.post')
    def test_get_tenant_access_token(self, mock_post, client):
        """测试获取 Tenant Token"""
        # 模拟响应
        mock_response = Mock()
        mock_response.json.return_value = {
            'code': 0,
            'tenant_access_token': 'test-token-123',
            'expire': 7200
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # 调用
        token = client._get_tenant_access_token()
        
        # 验证
        assert token == 'test-token-123'
        assert client._tenant_token == 'test-token-123'
        mock_post.assert_called_once()
    
    @patch('api.feishu_client.requests.post')
    def test_get_tenant_access_token_error(self, mock_post, client):
        """测试获取 Token 失败"""
        # 模拟错误响应
        mock_response = Mock()
        mock_response.json.return_value = {
            'code': 99991663,
            'msg': 'app not found'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # 验证异常
        with pytest.raises(Exception) as exc_info:
            client._get_tenant_access_token()
        
        assert 'app not found' in str(exc_info.value)
    
    @patch('api.feishu_client.requests.request')
    @patch.object(FeishuClient, '_get_tenant_access_token')
    def test_request_success(self, mock_get_token, mock_request, client):
        """测试 API 请求成功"""
        # 模拟
        mock_get_token.return_value = 'test-token'
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'code': 0,
            'data': {'items': []}
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        # 调用
        result = client._request('GET', '/test-endpoint')
        
        # 验证
        assert result == {'items': []}
        mock_request.assert_called_once()
    
    @patch('api.feishu_client.requests.request')
    @patch.object(FeishuClient, '_get_tenant_access_token')
    def test_request_api_error(self, mock_get_token, mock_request, client):
        """测试 API 返回错误码"""
        mock_get_token.return_value = 'test-token'
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'code': 99991661,
            'msg': 'tenant access token invalid'
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        # 验证异常
        with pytest.raises(Exception) as exc_info:
            client._request('GET', '/test-endpoint')
        
        assert 'tenant access token invalid' in str(exc_info.value)
    
    @patch.object(FeishuClient, '_request')
    def test_get_department_list(self, mock_request, client):
        """测试获取部门列表"""
        mock_request.return_value = {
            'items': [
                {'department_id': 'od-1', 'name': '部门1'},
                {'department_id': 'od-2', 'name': '部门2'}
            ],
            'has_more': False
        }
        
        result = client.get_department_list()
        
        assert len(result) == 2
        assert result[0]['name'] == '部门1'
    
    @patch.object(FeishuClient, '_request')
    def test_get_user_list(self, mock_request, client):
        """测试获取用户列表"""
        mock_request.return_value = {
            'items': [
                {'user_id': 'ou-1', 'name': '用户1'},
                {'user_id': 'ou-2', 'name': '用户2'}
            ],
            'has_more': False
        }
        
        result = client.get_user_list('od-test')
        
        assert len(result) == 2
        assert result[0]['name'] == '用户1'
    
    @patch.object(FeishuClient, '_request')
    def test_get_user_detail(self, mock_request, client):
        """测试获取用户详情"""
        mock_request.return_value = {
            'user': {
                'user_id': 'ou-test',
                'name': '测试用户',
                'email': 'test@example.com'
            }
        }
        
        result = client.get_user_detail('ou-test')
        
        assert result['user']['name'] == '测试用户'
