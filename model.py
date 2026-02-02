# model.py - 完整版本（包含所有功能）
from datetime import datetime
import hashlib
import uuid
import json

from exts import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    nickname = db.Column(db.String(50))
    gender = db.Column(db.String(10), default='未设置')
    college = db.Column(db.String(50), default='未设置')
    avatar = db.Column(db.Text)  # base64图片
    email = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        """安全地设置密码（使用sha256+盐值）"""
        salt = uuid.uuid4().hex
        self.password_hash = hashlib.sha256((password + salt).encode()).hexdigest() + ':' + salt

    def check_password(self, password):
        """验证密码"""
        if not self.password_hash or ':' not in self.password_hash:
            return False
        hashed, salt = self.password_hash.split(':')
        return hashed == hashlib.sha256((password + salt).encode()).hexdigest()

    def to_dict(self):
        """将用户对象转为字典（用于JSON响应）"""
        return {
            'id': self.id,
            'username': self.username,
            'student_id': self.student_id,
            'nickname': self.nickname or self.username,
            'gender': self.gender,
            'college': self.college,
            'avatar': self.avatar,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'email': self.email
        }


class CampusMemory(db.Model):
    __tablename__ = 'campus_memories'

    id = db.Column(db.Integer, primary_key=True)
    building = db.Column(db.String(50), nullable=False)  # 建筑名称
    content = db.Column(db.Text, nullable=False)  # 记忆内容
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    images = db.Column(db.Text, default='[]')  # 存储图片的JSON字符串数组
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 建立与用户的关系
    user = db.relationship('User', backref='campus_memories')

    def to_dict(self):
        """将记忆对象转为字典"""
        return {
            'id': self.id,
            'building': self.building,
            'content': self.content,
            'user_id': self.user_id,
            'images': json.loads(self.images) if self.images else [],
            'likes_count': self.likes_count,
            'comments_count': self.comments_count,
            'user_info': {
                'username': self.user.username,
                'nickname': self.user.nickname or self.user.username,
                'avatar': self.user.avatar,
                'college': self.user.college,
                'gender': self.user.gender
            } if self.user else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

    def to_frontend_dict(self):
        """为前端优化的格式"""
        images = []
        if self.images:
            try:
                images = json.loads(self.images)
            except:
                images = []

        return {
            'id': self.id,
            'building': self.building,
            'content': self.content,
            'name': self.user.nickname or self.user.username if self.user else '匿名',
            'avatar': self.user.avatar if self.user else '/static/default-avatar.jpg',
            'images': images,
            'likes_count': self.likes_count,
            'comments_count': self.comments_count,
            'time': self.created_at.strftime('%m-%d %H:%M') if self.created_at else '',
            'full_time': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            'user_id': self.user_id
        }


class Diary(db.Model):
    __tablename__ = 'diaries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    location = db.Column(db.String(50), nullable=False)  # 地点名称
    content = db.Column(db.Text, nullable=False)  # 日记内容
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 建立与用户的关系
    user = db.relationship('User', backref='diaries')

    def to_dict(self):
        """将日记对象转为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'location': self.location,
            'content': self.content,
            'user_info': {
                'username': self.user.username,
                'nickname': self.user.nickname or self.user.username,
                'avatar': self.user.avatar,
                'college': self.user.college
            } if self.user else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class MemoryComment(db.Model):
    __tablename__ = 'memory_comments'

    id = db.Column(db.Integer, primary_key=True)
    memory_id = db.Column(db.Integer, db.ForeignKey('campus_memories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('memory_comments.id'), nullable=True)  # 回复的评论ID
    content = db.Column(db.Text, nullable=False)
    likes_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 建立关系
    memory = db.relationship('CampusMemory', backref='memory_comments')
    user = db.relationship('User', backref='memory_comments')
    parent = db.relationship('MemoryComment', remote_side=[id], backref='replies')

    def to_dict(self):
        """将评论对象转为字典"""
        return {
            'id': self.id,
            'memory_id': self.memory_id,
            'user_id': self.user_id,
            'parent_id': self.parent_id,
            'content': self.content,
            'likes_count': self.likes_count,
            'user_info': {
                'username': self.user.username,
                'nickname': self.user.nickname or self.user.username,
                'avatar': self.user.avatar
            } if self.user else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class MemoryLike(db.Model):
    __tablename__ = 'memory_likes'

    id = db.Column(db.Integer, primary_key=True)
    memory_id = db.Column(db.Integer, db.ForeignKey('campus_memories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 建立唯一约束：一个用户只能给一条记忆点一次赞
    __table_args__ = (
        db.UniqueConstraint('memory_id', 'user_id', name='uq_memory_user_like'),
    )

    # 建立关系
    memory = db.relationship('CampusMemory', backref='memory_likes')
    user = db.relationship('User', backref='memory_likes')

    def to_dict(self):
        """将点赞对象转为字典"""
        return {
            'id': self.id,
            'memory_id': self.memory_id,
            'user_id': self.user_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class CommentLike(db.Model):
    __tablename__ = 'comment_likes'

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('memory_comments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 建立唯一约束：一个用户只能给一条评论点一次赞
    __table_args__ = (
        db.UniqueConstraint('comment_id', 'user_id', name='uq_comment_user_like'),
    )

    # 建立关系
    comment = db.relationship('MemoryComment', backref='comment_likes')
    user = db.relationship('User', backref='comment_likes')

    def to_dict(self):
        """将评论点赞对象转为字典"""
        return {
            'id': self.id,
            'comment_id': self.comment_id,
            'user_id': self.user_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 接收用户
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 发送用户
    type = db.Column(db.String(20), nullable=False)  # 'like_memory', 'like_comment', 'comment', 'reply', 'system'
    memory_id = db.Column(db.Integer, db.ForeignKey('campus_memories.id'), nullable=True)  # 相关记忆
    comment_id = db.Column(db.Integer, db.ForeignKey('memory_comments.id'), nullable=True)  # 相关评论
    content = db.Column(db.Text)  # 通知内容
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 建立关系
    user = db.relationship('User', foreign_keys=[user_id], backref='received_notifications')
    from_user = db.relationship('User', foreign_keys=[from_user_id], backref='sent_notifications')
    memory = db.relationship('CampusMemory', backref='notifications')
    comment = db.relationship('MemoryComment', backref='notifications')

    def to_dict(self):
        """将通知对象转为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'from_user_info': {
                'username': self.from_user.username,
                'nickname': self.from_user.nickname or self.from_user.username,
                'avatar': self.from_user.avatar
            } if self.from_user else None,
            'type': self.type,
            'memory_id': self.memory_id,
            'comment_id': self.comment_id,
            'content': self.content,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Building(db.Model):
    __tablename__ = 'buildings'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # 建筑名称
    description = db.Column(db.Text)  # 建筑描述
    image_url = db.Column(db.String(200))  # 建筑图片URL
    memories_count = db.Column(db.Integer, default=0)  # 相关记忆数量
    diaries_count = db.Column(db.Integer, default=0)  # 相关日记数量
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """将建筑对象转为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'image_url': self.image_url,
            'memories_count': self.memories_count,
            'diaries_count': self.diaries_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class UserActivity(db.Model):
    __tablename__ = 'user_activities'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(30),
                              nullable=False)  # 'login', 'logout', 'add_memory', 'add_diary', 'like', 'comment'
    target_type = db.Column(db.String(20), nullable=True)  # 'memory', 'diary', 'comment', 'user'
    target_id = db.Column(db.Integer, nullable=True)  # 目标ID
    ip_address = db.Column(db.String(45))  # IP地址
    user_agent = db.Column(db.Text)  # 用户代理
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 建立关系
    user = db.relationship('User', backref='activities')

    def to_dict(self):
        """将用户活动对象转为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'activity_type': self.activity_type,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent[:200] if self.user_agent else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }