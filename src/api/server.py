"""
API Server
提供组织架构查询接口
"""
import logging
from datetime import datetime
from typing import Optional, List
from flask import Flask, request, jsonify
from sqlalchemy.orm import Session

from ..db.models import Database, Department, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 全局数据库实例
db_instance = None

def init_api(db: Database):
    """初始化 API"""
    global db_instance
    db_instance = db


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/departments', methods=['GET'])
def list_departments():
    """获取部门列表"""
    session = db_instance.get_session()
    try:
        # 查询参数
        parent_id = request.args.get('parent_id')
        name = request.args.get('name')
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 20))
        
        # 构建查询
        query = session.query(Department).filter_by(status=1)
        
        if parent_id:
            query = query.filter_by(parent_id=parent_id)
        if name:
            query = query.filter(Department.name.like(f'%{name}%'))
        
        # 分页
        total = query.count()
        departments = query.offset((page - 1) * size).limit(size).all()
        
        return jsonify({
            'code': 0,
            'data': {
                'items': [d.to_dict() for d in departments],
                'total': total,
                'page': page,
                'size': size
            }
        })
    finally:
        session.close()


@app.route('/api/departments/<dept_id>', methods=['GET'])
def get_department(dept_id: str):
    """获取部门详情"""
    session = db_instance.get_session()
    try:
        dept = session.query(Department).filter_by(id=dept_id, status=1).first()
        
        if not dept:
            return jsonify({'code': 404, 'msg': '部门不存在'}), 404
        
        # 获取子部门
        children = session.query(Department).filter_by(parent_id=dept_id, status=1).all()
        
        result = dept.to_dict()
        result['children'] = [c.to_dict() for c in children]
        
        return jsonify({
            'code': 0,
            'data': result
        })
    finally:
        session.close()


@app.route('/api/departments/tree', methods=['GET'])
def get_department_tree():
    """获取部门树"""
    session = db_instance.get_session()
    try:
        # 获取所有部门
        departments = session.query(Department).filter_by(status=1).all()
        
        # 构建树形结构
        dept_map = {d.id: d.to_dict() for d in departments}
        tree = []
        
        for dept in departments:
            dept_dict = dept_map[dept.id]
            dept_dict['children'] = []
            
            if dept.parent_id and dept.parent_id in dept_map:
                parent = dept_map[dept.parent_id]
                if 'children' not in parent:
                    parent['children'] = []
                parent['children'].append(dept_dict)
            else:
                tree.append(dept_dict)
        
        return jsonify({
            'code': 0,
            'data': tree
        })
    finally:
        session.close()


@app.route('/api/users', methods=['GET'])
def list_users():
    """获取用户列表"""
    session = db_instance.get_session()
    try:
        # 查询参数
        department_id = request.args.get('department_id')
        name = request.args.get('name')
        email = request.args.get('email')
        status = request.args.get('status', '1')
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 20))
        
        # 构建查询
        query = session.query(User)
        
        if department_id:
            query = query.filter_by(department_id=department_id)
        if name:
            query = query.filter(User.name.like(f'%{name}%'))
        if email:
            query = query.filter(User.email.like(f'%{email}%'))
        if status:
            query = query.filter_by(status=int(status))
        
        # 分页
        total = query.count()
        users = query.offset((page - 1) * size).limit(size).all()
        
        return jsonify({
            'code': 0,
            'data': {
                'items': [u.to_dict() for u in users],
                'total': total,
                'page': page,
                'size': size
            }
        })
    finally:
        session.close()


@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id: str):
    """获取用户详情"""
    session = db_instance.get_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        
        if not user:
            return jsonify({'code': 404, 'msg': '用户不存在'}), 404
        
        result = user.to_dict()
        
        # 获取部门信息
        if user.department:
            result['department_name'] = user.department.name
        
        return jsonify({
            'code': 0,
            'data': result
        })
    finally:
        session.close()


@app.route('/api/users/search', methods=['GET'])
def search_users():
    """搜索用户"""
    session = db_instance.get_session()
    try:
        keyword = request.args.get('q', '')
        if not keyword or len(keyword) < 2:
            return jsonify({'code': 400, 'msg': '搜索关键词至少需要2个字符'}), 400
        
        # 多字段搜索
        users = session.query(User).filter(
            (User.name.like(f'%{keyword}%')) |
            (User.email.like(f'%{keyword}%')) |
            (User.mobile.like(f'%{keyword}%')) |
            (User.employee_no.like(f'%{keyword}%'))
        ).filter_by(status=1).limit(20).all()
        
        return jsonify({
            'code': 0,
            'data': [u.to_dict() for u in users]
        })
    finally:
        session.close()


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    session = db_instance.get_session()
    try:
        dept_count = session.query(Department).filter_by(status=1).count()
        user_count = session.query(User).filter_by(status=1).count()
        inactive_user_count = session.query(User).filter_by(status=2).count()
        
        return jsonify({
            'code': 0,
            'data': {
                'departments': {
                    'total': dept_count
                },
                'users': {
                    'active': user_count,
                    'inactive': inactive_user_count,
                    'total': user_count + inactive_user_count
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        })
    finally:
        session.close()


def run_api_server(host='0.0.0.0', port=8000, debug=False):
    """运行 API 服务器"""
    logger.info(f"启动 API 服务器: {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_api_server()
