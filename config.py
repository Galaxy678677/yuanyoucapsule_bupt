import os

SQLALCHEMY_DATABASE_URI= "mysql+pymysql://root:zong15511970268@127.0.0.1/chuyanplan?charset=utf8mb4"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 会话安全
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this-in-production'

# 文件上传
MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 最大上传2MB
UPLOAD_FOLDER = 'uploads'  # 如果需要保存文件而不是base64

# 会话配置
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # 生产环境应设为True（HTTPS）
PERMANENT_SESSION_LIFETIME = 86400  # 24小时