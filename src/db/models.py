"""
数据库模型定义
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

Base = declarative_base()

class Department(Base):
    """部门表"""
    __tablename__ = 'departments'
    
    id = Column(String(64), primary_key=True)  # 飞书部门ID
    name = Column(String(255), nullable=False)  # 部门名称
    parent_id = Column(String(64), ForeignKey('departments.id'), nullable=True)  # 父部门ID
    leader_user_id = Column(String(64), nullable=True)  # 部门负责人ID
    order = Column(Integer, default=0)  # 排序
    status = Column(Integer, default=1)  # 状态：1-正常，0-禁用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    synced_at = Column(DateTime, default=datetime.utcnow)  # 最后同步时间
    
    # 关系
    parent = relationship("Department", remote_side=[id], backref="children")
    users = relationship("User", back_populates="department")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'leader_user_id': self.leader_user_id,
            'order': self.order,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(String(64), primary_key=True)  # 飞书用户ID (open_id)
    union_id = Column(String(64), unique=True, nullable=True)  # 统一ID
    user_id = Column(String(64), unique=True, nullable=True)  # 用户自定义ID
    name = Column(String(255), nullable=False)  # 姓名
    en_name = Column(String(255), nullable=True)  # 英文名
    email = Column(String(255), nullable=True)  # 邮箱
    mobile = Column(String(20), nullable=True)  # 手机号
    avatar_url = Column(Text, nullable=True)  # 头像URL
    department_id = Column(String(64), ForeignKey('departments.id'), nullable=True)  # 主部门ID
    employee_no = Column(String(64), nullable=True)  # 员工编号
    employee_type = Column(Integer, default=1)  # 员工类型：1-正式，2-实习生，3-外包
    status = Column(Integer, default=1)  # 状态：1-在职，2-离职
    gender = Column(Integer, nullable=True)  # 性别：0-未知，1-男，2-女
    city = Column(String(100), nullable=True)  # 城市
    country = Column(String(100), nullable=True)  # 国家
    job_title = Column(String(255), nullable=True)  # 职位
    is_tenant_manager = Column(Integer, default=0)  # 是否租户管理员
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    synced_at = Column(DateTime, default=datetime.utcnow)  # 最后同步时间
    
    # 关系
    department = relationship("Department", back_populates="users")
    
    def to_dict(self):
        return {
            'id': self.id,
            'union_id': self.union_id,
            'user_id': self.user_id,
            'name': self.name,
            'en_name': self.en_name,
            'email': self.email,
            'mobile': self.mobile,
            'department_id': self.department_id,
            'employee_no': self.employee_no,
            'employee_type': self.employee_type,
            'status': self.status,
            'gender': self.gender,
            'city': self.city,
            'job_title': self.job_title,
            'is_tenant_manager': self.is_tenant_manager,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SyncLog(Base):
    """同步日志表"""
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String(50), nullable=False)  # 同步类型：full/incremental/webhook
    entity_type = Column(String(50), nullable=False)  # 实体类型：user/department
    entity_id = Column(String(64), nullable=True)  # 实体ID
    action = Column(String(50), nullable=False)  # 操作：create/update/delete
    status = Column(String(20), nullable=False)  # 状态：success/failed
    message = Column(Text, nullable=True)  # 消息/错误信息
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sync_type': self.sync_type,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'action': self.action,
            'status': self.status,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# 数据库连接管理
class Database:
    def __init__(self, db_url=None):
        if db_url is None:
            db_path = os.getenv('DATABASE_PATH', '/app/data/org_sync.db')
            db_url = f'sqlite:///{db_path}'
        
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 创建表
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        return self.SessionLocal()
    
    def close(self):
        self.engine.dispose()


# 全局数据库实例
db = Database()
