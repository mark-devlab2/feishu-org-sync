#!/usr/bin/env python3
"""
Feishu Organization Sync CLI
组织架构查询命令行工具
"""
import os
import sys
import click
from pathlib import Path
from tabulate import tabulate

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.models import Database
from api.feishu_client import FeishuClient
from sync.sync_service import SyncService

# 全局数据库实例
db = None

def get_db():
    """获取数据库实例"""
    global db
    if db is None:
        db_path = os.getenv('DATABASE_PATH', '/app/data/org_sync.db')
        db = Database(f'sqlite:///{db_path}')
    return db


@click.group()
@click.option('--db-path', envvar='DATABASE_PATH', help='数据库路径')
@click.pass_context
def cli(ctx, db_path):
    """Feishu Organization Sync CLI - 组织架构查询工具"""
    ctx.ensure_object(dict)
    if db_path:
        ctx.obj['db_path'] = db_path
        global db
        db = Database(f'sqlite:///{db_path}')


@cli.command()
@click.option('--dept-id', default='0', help='父部门ID，默认为根部门')
@click.option('--format', 'fmt', default='table', type=click.Choice(['table', 'json']), help='输出格式')
def departments(dept_id, fmt):
    """列出部门"""
    from sqlalchemy.orm import Session
    
    session = get_db().get_session()
    try:
        from db.models import Department
        
        depts = session.query(Department).filter_by(parent_id=dept_id if dept_id != '0' else None, status=1).all()
        
        if not depts:
            click.echo("未找到部门")
            return
        
        data = [[d.id, d.name, d.parent_id or '-', len(d.users)] for d in depts]
        
        if fmt == 'json':
            import json
            click.echo(json.dumps([d.to_dict() for d in depts], indent=2, ensure_ascii=False))
        else:
            headers = ['ID', '名称', '父部门', '人数']
            click.echo(tabulate(data, headers=headers, tablefmt='grid'))
            click.echo(f"\n共 {len(depts)} 个部门")
    finally:
        session.close()


@cli.command()
@click.option('--dept-id', help='按部门筛选')
@click.option('--name', help='按姓名搜索')
@click.option('--status', default='1', help='状态：1-在职，2-离职')
@click.option('--limit', default=20, help='返回数量限制')
@click.option('--format', 'fmt', default='table', type=click.Choice(['table', 'json']), help='输出格式')
def users(dept_id, name, status, limit, fmt):
    """列出用户"""
    from sqlalchemy.orm import Session
    from db.models import User
    
    session = get_db().get_session()
    try:
        query = session.query(User)
        
        if dept_id:
            query = query.filter_by(department_id=dept_id)
        if name:
            query = query.filter(User.name.like(f'%{name}%'))
        if status:
            query = query.filter_by(status=int(status))
        
        users = query.limit(limit).all()
        
        if not users:
            click.echo("未找到用户")
            return
        
        data = []
        for u in users:
            dept_name = u.department.name if u.department else '-'
            data.append([
                u.id[:20] + '...' if len(u.id) > 20 else u.id,
                u.name,
                u.email or '-',
                u.mobile or '-',
                dept_name,
                '在职' if u.status == 1 else '离职'
            ])
        
        if fmt == 'json':
            import json
            click.echo(json.dumps([u.to_dict() for u in users], indent=2, ensure_ascii=False))
        else:
            headers = ['ID', '姓名', '邮箱', '手机', '部门', '状态']
            click.echo(tabulate(data, headers=headers, tablefmt='grid'))
            click.echo(f"\n共 {len(users)} 个用户")
    finally:
        session.close()


@cli.command()
@click.argument('keyword')
def search(keyword):
    """搜索用户"""
    from sqlalchemy.orm import Session
    from db.models import User
    
    session = get_db().get_session()
    try:
        users = session.query(User).filter(
            (User.name.like(f'%{keyword}%')) |
            (User.email.like(f'%{keyword}%')) |
            (User.mobile.like(f'%{keyword}%'))
        ).limit(10).all()
        
        if not users:
            click.echo(f"未找到包含 '{keyword}' 的用户")
            return
        
        data = []
        for u in users:
            dept_name = u.department.name if u.department else '-'
            data.append([u.name, u.email or '-', u.mobile or '-', dept_name])
        
        headers = ['姓名', '邮箱', '手机', '部门']
        click.echo(tabulate(data, headers=headers, tablefmt='grid'))
    finally:
        session.close()


@cli.command()
def stats():
    """显示统计信息"""
    from sqlalchemy.orm import Session
    from db.models import Department, User
    
    session = get_db().get_session()
    try:
        dept_count = session.query(Department).filter_by(status=1).count()
        user_active = session.query(User).filter_by(status=1).count()
        user_inactive = session.query(User).filter_by(status=2).count()
        
        click.echo("=" * 40)
        click.echo("组织架构统计")
        click.echo("=" * 40)
        click.echo(f"部门总数:     {dept_count}")
        click.echo(f"在职员工:     {user_active}")
        click.echo(f"离职员工:     {user_inactive}")
        click.echo(f"员工总数:     {user_active + user_inactive}")
        click.echo("=" * 40)
    finally:
        session.close()


@cli.command()
@click.option('--app-id', envvar='FEISHU_APP_ID', required=True, help='飞书 App ID')
@click.option('--app-secret', envvar='FEISHU_APP_SECRET', required=True, help='飞书 App Secret')
def sync(app_id, app_secret):
    """手动执行全量同步"""
    click.echo("开始全量同步...")
    
    client = FeishuClient(app_id, app_secret)
    service = SyncService(get_db(), client)
    
    try:
        result = service.full_sync()
        
        click.echo("\n同步完成!")
        click.echo(f"部门: 新建 {result['departments']['created']}, 更新 {result['departments']['updated']}, 失败 {result['departments']['failed']}")
        click.echo(f"用户: 新建 {result['users']['created']}, 更新 {result['users']['updated']}, 失败 {result['users']['failed']}")
    except Exception as e:
        click.echo(f"同步失败: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
