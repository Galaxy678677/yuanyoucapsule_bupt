# config.py - Railway专用版本
import os
from urllib.parse import urlparse

# ===== 环境检测 =====
IS_RAILWAY = 'RAILWAY_ENVIRONMENT' in os.environ
IS_PRODUCTION = os.environ.get('ENVIRONMENT') == 'production'

# ===== 数据库配置 =====
# Railway提供DATABASE_URL环境变量
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # 解析DATABASE_URL（支持PostgreSQL）
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
else:
    # 如果没有DATABASE_URL，使用SQLite（开发环境）
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{BASE_DIR}/app.db'

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

# ===== 会话安全 =====
# Railway会自动设置SECRET_KEY环境变量
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this-in-production')

# ===== 文件上传 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大上传16MB

# ===== 会话配置 =====
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = IS_PRODUCTION  # 生产环境启用HTTPS
SESSION_COOKIE_SAMESITE = 'Lax'
PERMANENT_SESSION_LIFETIME = 86400  # 24小时