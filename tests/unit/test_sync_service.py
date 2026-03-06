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
        result = sync_service._sync_departments(db_session)
        
        # 验证结果
        assert result['created'] == 2
        assert result['failed'] == 0
        
        # 验证数据库
        depts = db_session.query(Department).all()
        assert len(depts) == 2
        assert depts[0].name == '技术部'
    
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
        
        # 直接调用处理方法
        sync_service._handle_user_change(db_session, 'ou-1', 'delete')
        db_session.commit()
        
        # 验证用户被标记为离职
        deleted_user = db_session.query(User).filter_by(id='ou-1').first()
        assert deleted_user.status == 2  # 离职状态
    
    def test_sync_logs_created(self, sync_service, mock_client, db_session):
        """测试同步日志记录"""
        mock_client.get_department_list.return_value = [
            {'department_id': 'od-1', 'name': '技术部', 'parent_department_id': '0'}
        ]
        
        sync_service._sync_departments(db_session)
        
        # 验证日志
        logs = db_session.query(SyncLog).all()
        assert len(logs) > 0
        assert logs[0].entity_type == 'department'
        assert logs[0].status == 'success'
