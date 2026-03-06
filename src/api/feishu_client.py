"""
飞书 API 客户端
封装通讯录相关 API 调用
"""
import requests
import time
from typing import List, Dict, Optional, Generator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeishuClient:
    """飞书 API 客户端"""
    
    def __init__(self, app_id: str, app_secret: str, domain: str = "https://open.feishu.cn"):
        self.app_id = app_id
        self.app_secret = app_secret
        self.domain = domain.rstrip('/')
        self._tenant_token = None
        self._token_expire_time = 0
    
    def _get_tenant_access_token(self) -> str:
        """获取 Tenant Access Token（带缓存）"""
        # 如果 token 还有效，直接返回
        if self._tenant_token and time.time() < self._token_expire_time - 300:
            return self._tenant_token
        
        url = f"{self.domain}/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 0:
                self._tenant_token = result['tenant_access_token']
                expire = result.get('expire', 7200)
                self._token_expire_time = time.time() + expire
                logger.info("Tenant Access Token 已更新")
                return self._tenant_token
            else:
                raise Exception(f"获取 Token 失败: {result}")
                
        except Exception as e:
            logger.error(f"请求 Token 失败: {e}")
            raise
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """发送 API 请求"""
        url = f"{self.domain}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f"Bearer {self._get_tenant_access_token()}"
        
        try:
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') != 0:
                raise Exception(f"API 错误: {result.get('msg')} (code: {result.get('code')})")
            
            return result.get('data', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            raise
    
    def get_department_list(self, parent_department_id: str = "0", fetch_child: bool = True) -> List[Dict]:
        """
        获取部门列表
        
        Args:
            parent_department_id: 父部门ID，默认为0（根部门）
            fetch_child: 是否递归获取子部门
        
        Returns:
            部门列表
        """
        departments = []
        page_token = None
        
        while True:
            params = {
                "parent_department_id": parent_department_id,
                "fetch_child": fetch_child,
                "page_size": 50
            }
            if page_token:
                params["page_token"] = page_token
            
            data = self._request("GET", "/open-apis/contact/v3/department/simple/list", params=params)
            
            items = data.get('items', [])
            departments.extend(items)
            
            page_token = data.get('page_token')
            if not page_token or not data.get('has_more'):
                break
        
        logger.info(f"获取到 {len(departments)} 个部门")
        return departments
    
    def get_department_detail(self, department_id: str) -> Dict:
        """获取部门详情"""
        data = self._request(
            "GET", 
            f"/open-apis/contact/v3/department/{department_id}"
        )
        return data.get('department', {})
    
    def get_user_list(self, department_id: str) -> List[Dict]:
        """
        获取部门下的用户列表
        
        Args:
            department_id: 部门ID
        
        Returns:
            用户列表
        """
        users = []
        page_token = None
        
        while True:
            params = {
                "department_id": department_id,
                "page_size": 50
            }
            if page_token:
                params["page_token"] = page_token
            
            data = self._request("GET", "/open-apis/contact/v3/user/simple/list", params=params)
            
            items = data.get('items', [])
            users.extend(items)
            
            page_token = data.get('page_token')
            if not page_token or not data.get('has_more'):
                break
        
        logger.info(f"部门 {department_id} 下获取到 {len(users)} 个用户")
        return users
    
    def get_user_detail(self, user_id: str) -> Dict:
        """获取用户详情"""
        data = self._request(
            "GET", 
            f"/open-apis/contact/v3/users/{user_id}"
        )
        return data
    
    def get_all_users(self) -> Generator[Dict, None, None]:
        """
        获取所有用户（生成器）
        
        Yields:
            用户信息
        """
        # 先获取所有部门
        departments = self.get_department_list()
        
        seen_user_ids = set()
        
        for dept in departments:
            dept_id = dept.get('department_id')
            users = self.get_user_list(dept_id)
            
            for user in users:
                user_id = user.get('user_id')
                if user_id and user_id not in seen_user_ids:
                    seen_user_ids.add(user_id)
                    yield user
    
    def get_user_batch(self, user_ids: List[str]) -> List[Dict]:
        """批量获取用户信息"""
        if not user_ids:
            return []
        
        # 飞书限制每次最多 50 个
        batch_size = 50
        results = []
        
        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]
            
            data = self._request(
                "POST",
                "/open-apis/contact/v3/users/batch",
                json={"user_ids": batch}
            )
            
            users = data.get('users', [])
            results.extend(users)
        
        return results
