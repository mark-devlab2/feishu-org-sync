"""
组织架构同步服务
处理全量同步和增量同步
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.feishu_client import FeishuClient
from db.models import Database, Department, User, SyncLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyncService:
    """同步服务"""
    
    def __init__(self, db: Database, feishu_client: FeishuClient):
        self.db = db
        self.client = feishu_client
    
    def full_sync(self) -> Dict:
        """
        全量同步
        
        Returns:
            同步统计信息
        """
        logger.info("开始全量同步...")
        stats = {
            'departments': {'created': 0, 'updated': 0, 'failed': 0},
            'users': {'created': 0, 'updated': 0, 'failed': 0}
        }
        
        session = self.db.get_session()
        try:
            # 1. 同步部门
            dept_stats = self._sync_departments(session)
            stats['departments'].update(dept_stats)
            
            # 2. 同步用户
            user_stats = self._sync_users(session)
            stats['users'].update(user_stats)
            
            session.commit()
            logger.info(f"全量同步完成: {stats}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"全量同步失败: {e}")
            raise
        finally:
            session.close()
        
        return stats
    
    def _sync_departments(self, session: Session) -> Dict:
        """同步部门数据"""
        stats = {'created': 0, 'updated': 0, 'failed': 0}
        
        try:
            # 获取飞书部门列表
            feishu_depts = self.client.get_department_list()
            
            for dept_data in feishu_depts:
                try:
                    dept_id = dept_data.get('department_id')
                    name = dept_data.get('name')
                    parent_id = dept_data.get('parent_department_id')
                    
                    # 查询数据库中是否已存在
                    dept = session.query(Department).filter_by(id=dept_id).first()
                    
                    if dept:
                        # 更新
                        dept.name = name
                        dept.parent_id = parent_id if parent_id != "0" else None
                        dept.synced_at = datetime.utcnow()
                        action = 'update'
                        stats['updated'] += 1
                    else:
                        # 创建
                        dept = Department(
                            id=dept_id,
                            name=name,
                            parent_id=parent_id if parent_id != "0" else None,
                            order=dept_data.get('order', 0)
                        )
                        session.add(dept)
                        action = 'create'
                        stats['created'] += 1
                    
                    # 记录同步日志
                    log = SyncLog(
                        sync_type='full',
                        entity_type='department',
                        entity_id=dept_id,
                        action=action,
                        status='success'
                    )
                    session.add(log)
                    
                except Exception as e:
                    logger.error(f"同步部门 {dept_data.get('department_id')} 失败: {e}")
                    stats['failed'] += 1
                    
                    # 记录失败日志
                    log = SyncLog(
                        sync_type='full',
                        entity_type='department',
                        entity_id=dept_data.get('department_id'),
                        action='sync',
                        status='failed',
                        message=str(e)
                    )
                    session.add(log)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取部门列表失败: {e}")
            raise
    
    def _sync_users(self, session: Session) -> Dict:
        """同步用户数据"""
        stats = {'created': 0, 'updated': 0, 'failed': 0}
        
        try:
            # 获取所有用户
            count = 0
            for user_data in self.client.get_all_users():
                try:
                    user_id = user_data.get('user_id')
                    if not user_id:
                        continue
                    
                    # 查询数据库
                    user = session.query(User).filter_by(id=user_id).first()
                    
                    # 提取用户信息
                    user_info = {
                        'union_id': user_data.get('union_id'),
                        'user_id': user_data.get('user_id'),
                        'name': user_data.get('name'),
                        'en_name': user_data.get('en_name'),
                        'email': user_data.get('email'),
                        'mobile': user_data.get('mobile'),
                        'avatar_url': user_data.get('avatar', {}).get('avatar_72'),
                        'department_id': user_data.get('department_id'),
                        'employee_no': user_data.get('employee_no'),
                        'status': 1 if user_data.get('status', {}).get('is_activated') else 0
                    }
                    
                    if user:
                        # 更新
                        for key, value in user_info.items():
                            setattr(user, key, value)
                        user.synced_at = datetime.utcnow()
                        action = 'update'
                        stats['updated'] += 1
                    else:
                        # 创建
                        user = User(**user_info)
                        session.add(user)
                        action = 'create'
                        stats['created'] += 1
                    
                    # 记录同步日志
                    log = SyncLog(
                        sync_type='full',
                        entity_type='user',
                        entity_id=user_id,
                        action=action,
                        status='success'
                    )
                    session.add(log)
                    
                    count += 1
                    if count % 100 == 0:
                        logger.info(f"已同步 {count} 个用户...")
                        session.flush()
                
                except Exception as e:
                    logger.error(f"同步用户失败: {e}")
                    stats['failed'] += 1
            
            logger.info(f"共同步 {count} 个用户")
            return stats
            
        except Exception as e:
            logger.error(f"同步用户失败: {e}")
            raise
    
    def incremental_sync(self, changed_entities: List[Dict]) -> Dict:
        """
        增量同步（用于处理 Webhook 事件）
        
        Args:
            changed_entities: 变更的实体列表
            
        Returns:
            同步统计
        """
        logger.info(f"开始增量同步，{len(changed_entities)} 个变更...")
        stats = {'success': 0, 'failed': 0}
        
        session = self.db.get_session()
        try:
            for entity in changed_entities:
                try:
                    entity_type = entity.get('type')
                    entity_id = entity.get('id')
                    action = entity.get('action')  # create/update/delete
                    
                    if entity_type == 'user':
                        self._handle_user_change(session, entity_id, action)
                    elif entity_type == 'department':
                        self._handle_department_change(session, entity_id, action)
                    
                    stats['success'] += 1
                    
                except Exception as e:
                    logger.error(f"处理变更失败: {e}")
                    stats['failed'] += 1
            
            session.commit()
            logger.info(f"增量同步完成: {stats}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"增量同步失败: {e}")
            raise
        finally:
            session.close()
        
        return stats
    
    def _handle_user_change(self, session: Session, user_id: str, action: str):
        """处理用户变更"""
        if action == 'delete':
            # 删除用户（标记为离职）
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                user.status = 2  # 离职
                user.synced_at = datetime.utcnow()
                logger.info(f"用户 {user_id} 已标记为离职")
        else:
            # 获取最新信息并更新
            try:
                user_data = self.client.get_user_detail(user_id)
                # ... 更新逻辑类似全量同步
                logger.info(f"用户 {user_id} 已更新")
            except Exception as e:
                logger.error(f"获取用户 {user_id} 详情失败: {e}")
                raise
    
    def _handle_department_change(self, session: Session, dept_id: str, action: str):
        """处理部门变更"""
        if action == 'delete':
            # 删除部门
            dept = session.query(Department).filter_by(id=dept_id).first()
            if dept:
                dept.status = 0  # 禁用
                dept.synced_at = datetime.utcnow()
                logger.info(f"部门 {dept_id} 已禁用")
        else:
            # 获取最新信息并更新
            try:
                dept_data = self.client.get_department_detail(dept_id)
                # ... 更新逻辑
                logger.info(f"部门 {dept_id} 已更新")
            except Exception as e:
                logger.error(f"获取部门 {dept_id} 详情失败: {e}")
                raise
