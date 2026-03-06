"""
数据库模型单元测试
"""
import pytest
from datetime import datetime
from db.models import Department, User, SyncLog


class TestDepartment:
    """部门模型测试"""
    
    def test_create_department(self, db_session, sample_department):
        """测试创建部门"""
        dept = Department(**sample_department)
        db_session.add(dept)
        db_session.commit()
        
        # 验证
        result = db_session.query(Department).filter_by(id='od-test-001').first()
        assert result is not None
        assert result.name == '测试部门'
        assert result.status == 1
    
    def test_department_to_dict(self, sample_department):
        """测试部门序列化"""
        dept = Department(**sample_department)
        data = dept.to_dict()
        
        assert data['id'] == 'od-test-001'
        assert data['name'] == '测试部门'
        assert 'created_at' in data
    
    def test_department_parent_relationship(self, db_session):
        """测试部门父子关系"""
        # 创建父部门
        parent = Department(id='od-parent', name='父部门', status=1)
        db_session.add(parent)
        
        # 创建子部门
        child = Department(id='od-child', name='子部门', parent_id='od-parent', status=1)
        db_session.add(child)
        db_session.commit()
        
        # 验证关系
        parent_dept = db_session.query(Department).filter_by(id='od-parent').first()
        assert len(parent_dept.children) == 1
        assert parent_dept.children[0].name == '子部门'


class TestUser:
    """用户模型测试"""
    
    def test_create_user(self, db_session, sample_user):
        """测试创建用户"""
        user = User(**sample_user)
        db_session.add(user)
        db_session.commit()
        
        result = db_session.query(User).filter_by(id='ou-test-001').first()
        assert result is not None
        assert result.name == '测试用户'
        assert result.email == 'test@example.com'
    
    def test_user_to_dict(self, sample_user):
        """测试用户序列化"""
        user = User(**sample_user)
        data = user.to_dict()
        
        assert data['id'] == 'ou-test-001'
        assert data['name'] == '测试用户'
        assert data['email'] == 'test@example.com'
    
    def test_user_department_relationship(self, db_session, sample_department, sample_user):
        """测试用户部门关系"""
        # 创建部门
        dept = Department(**sample_department)
        db_session.add(dept)
        
        # 创建用户
        user = User(**sample_user)
        db_session.add(user)
        db_session.commit()
        
        # 验证关系
        user_result = db_session.query(User).filter_by(id='ou-test-001').first()
        assert user_result.department is not None
        assert user_result.department.name == '测试部门'


class TestSyncLog:
    """同步日志模型测试"""
    
    def test_create_sync_log(self, db_session):
        """测试创建同步日志"""
        log = SyncLog(
            sync_type='full',
            entity_type='user',
            entity_id='ou-test-001',
            action='create',
            status='success',
            message='测试消息'
        )
        db_session.add(log)
        db_session.commit()
        
        result = db_session.query(SyncLog).first()
        assert result is not None
        assert result.sync_type == 'full'
        assert result.status == 'success'
    
    def test_sync_log_to_dict(self):
        """测试同步日志序列化"""
        log = SyncLog(
            id=1,
            sync_type='incremental',
            entity_type='department',
            entity_id='od-test',
            action='update',
            status='success'
        )
        data = log.to_dict()
        
        assert data['sync_type'] == 'incremental'
        assert data['entity_type'] == 'department'
        assert data['status'] == 'success'
