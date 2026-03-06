"""
Pytest 配置文件
提供测试 fixtures
"""
import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加 src 到路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.models import Base, Department, User


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    # 使用内存数据库
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()


@pytest.fixture
def sample_department():
    """示例部门数据"""
    return {
        'id': 'od-test-001',
        'name': '测试部门',
        'parent_id': None,
        'leader_user_id': 'ou-test-leader',
        'order': 1,
        'status': 1
    }


@pytest.fixture
def sample_user():
    """示例用户数据"""
    return {
        'id': 'ou-test-001',
        'union_id': 'on-test-001',
        'user_id': 'test001',
        'name': '测试用户',
        'en_name': 'Test User',
        'email': 'test@example.com',
        'mobile': '13800138000',
        'department_id': 'od-test-001',
        'employee_no': 'E001',
        'status': 1,
        'gender': 1,
        'job_title': '工程师'
    }


@pytest.fixture
def mock_feishu_response():
    """模拟飞书 API 响应"""
    return {
        'code': 0,
        'msg': 'ok',
        'data': {}
    }
