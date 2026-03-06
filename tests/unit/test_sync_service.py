"""
同步服务单元测试
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from sync.sync_service import SyncService
from db.models import Department, User, SyncLog


class TestSyncService:
    """同步服务测试"""
    
    @pytest.fixture
    def mock_client(self):
        """模拟飞书客户端"""
        return Mock()
    
    @pytest.fixture
    def sync_service(self, db_session, mock_client):
        """创建同步服务"""
        from db.models import Database
        mock_db = Mock(spec=Database)
        mock_db.get_session.return_value = db_session
        return SyncService(mock_db, mock_client)
    
    def test_full_sync_departments(self, sync_service, mock_client, db_session):
        """测试全量同步部门"""
        # 模拟飞书返回数据
        mock_client.get_department_list.return_value = [
            {'department_id': 'od-1', 'name': '技术部', 'parent_department_id': '0'},
            {'department_id': 'od-2', 'name': '产品部', 'parent_department_id': '0'}
        ]
        
        # 执行同步
        result = sync_service.full_sync()
        
        # 验证结果
        assert result['departments']['created'] == 2
        assert result['departments']['failed'] == 0
        
        # 验证数据库
        depts = db_session.query(Department).all()
        assert len(depts) == 2
        assert depts[0].name == '技术部'
    
    def test_full_sync_users(self, sync_service, mock_client, db_session):
        """测试全量同步用户"""
        # 先创建部门
        dept = Department(id='od-1', name='技术部', status=1)
        db_session.add(dept)
        db_session.commit()
        
        # 模拟飞书返回数据
        mock_client.get_all_users.return_value = iter([
            {
                'user_id': 'ou-1',
                'name': '张三',
                'email': 'zhangsan@example.com',
                'department_id': 'od-1'
            },
            {
                'user_id': 'ou-2',
                'name': '李四',
                'email': 'lisi@example.com',
                'department_id': 'od-1'
            }
        ])
        
        # 执行同步
        with patch.object(sync_service, '_sync_departments', return_value={'created': 0, 'updated': 0, 'failed': 0}):
            result = sync_service.full_sync()
        
        # 验证
        assert result['users']['created'] == 2
        
        users = db_session.query(User).all()
        assert len(users) == 2
    
    def test_incremental_sync_user_update(self, sync_service, mock_client, db_session):
        """测试增量同步用户更新"""
        # 创建现有用户
        user = User(
            id='ou-1',
            name='旧名字',
            email='old@example.com',
            status=1
        )
        db_session.add(user)
        db_session.commit()
        
        # 模拟飞书返回新数据
        mock_client.get_user_detail.return_value = {
            'user': {
                'user_id': 'ou-1',
                'name': '新名字',
                'email': 'new@example.com'
            }
        }
        
        # 执行增量同步
        changes = [{
            'type': 'user',
            'id': 'ou-1',
            'action': 'update'
        }]
        
        result = sync_service.incremental_sync(changes)
        
        # 验证
        assert result['success'] == 1
        
        updated_user = db_session.query(User).filter_by(id='ou-1').first()
        assert updated_user.name == '新名字'
    
    def test_incremental_sync_user_delete(self, sync_service, db_session):
        """测试增量同步用户删除"""
        # 创建用户
        user = User(
            id='ou-1',
            name='张三',
            status=1
        )
        db_session.add(user)
        db_session.commit()
        
        # 执行删除同步
        changes = [{
            'type': 'user',
            'id': 'ou-1',
            'action': 'delete'
        }]
        
        result = sync_service.incremental_sync(changes)
        
        # 验证用户被标记为离职
        assert result['success'] == 1
        deleted_user = db_session.query(User).filter_by(id='ou-1').first()
        assert deleted_user.status == 2  # 离职状态
    
    def test_sync_logs_created(self, sync_service, mock_client, db_session):
        """测试同步日志记录"""
        mock_client.get_department_list.return_value = [
            {'department_id': 'od-1', 'name': '技术部', 'parent_department_id': '0'}
        ]
        
        sync_service.full_sync()
        
        # 验证日志
        logs = db_session.query(SyncLog).all()
        assert len(logs) > 0
        assert logs[0].entity_type == 'department'
        assert logs[0].status == 'success'
