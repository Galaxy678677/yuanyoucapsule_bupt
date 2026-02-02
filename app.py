# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory, session
import config
from exts import db, migrate
from model import User, CampusMemory, Diary, MemoryComment, MemoryLike, Notification  # 确保导入正确的模型
import base64
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.from_object(config)

# 确保SECRET_KEY已设置
if not app.config.get('SECRET_KEY'):
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')

db.init_app(app)
migrate.init_app(app, db)

# 允许的头像扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 创建uploads目录如果不存在
if not os.path.exists('uploads'):
    os.makedirs('uploads')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ========== 页面路由 ==========
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/campus')
def campus():
    return render_template('校园记忆.html')


@app.route('/my-bupt')
def my_bupt():
    return render_template('my-bupt.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


# ========== API路由 ==========
# API: 检查登录状态
@app.route('/api/check-login', methods=['GET'])
def check_login():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return jsonify({
                'success': True,
                'logged_in': True,
                'user': user.to_dict()
            })
    return jsonify({'success': True, 'logged_in': False})


# API: 用户注册
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json

        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'})

        # 检查必填字段
        if not all(k in data for k in ['username', 'password', 'student_id']):
            return jsonify({'success': False, 'message': '缺少必要字段'})

        # 验证输入
        if len(data['username']) < 3:
            return jsonify({'success': False, 'message': '用户名至少3个字符'})

        if len(data['password']) < 6:
            return jsonify({'success': False, 'message': '密码至少6个字符'})

        # 检查用户名是否已存在
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'message': '用户名已存在'})

        # 检查学号是否已存在
        if User.query.filter_by(student_id=data['student_id']).first():
            return jsonify({'success': False, 'message': '该学号已注册'})

        # 创建新用户
        new_user = User(
            username=data['username'],
            student_id=data['student_id'],
            nickname=data.get('nickname', data['username'])  # 默认昵称等于用户名
        )
        new_user.set_password(data['password'])

        db.session.add(new_user)
        db.session.commit()

        # 注册后自动登录
        session['user_id'] = new_user.id

        return jsonify({
            'success': True,
            'message': '注册成功',
            'user': new_user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'注册失败：{str(e)}'})


# API: 用户登录
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json

        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'})

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            return jsonify({'success': False, 'message': '请输入用户名和密码'})

        # 查找用户（支持用户名或学号登录）
        user = User.query.filter(
            (User.username == username) |
            (User.student_id == username)
        ).first()

        if not user:
            return jsonify({'success': False, 'message': '用户不存在'})

        if not user.check_password(password):
            return jsonify({'success': False, 'message': '密码错误'})

        # 登录成功，设置session
        session['user_id'] = user.id

        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '登录成功',
            'user': user.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'登录失败：{str(e)}'})


# API: 更新个人资料
@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'})

        # 如果是表单数据（包含文件）
        if request.content_type and 'multipart/form-data' in request.content_type:
            # 更新文本信息
            user.nickname = request.form.get('nickname', user.nickname)
            user.gender = request.form.get('gender', user.gender)
            user.college = request.form.get('college', user.college)

            # 处理头像上传
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and file.filename and allowed_file(file.filename):
                    # 将图片转为base64存储
                    avatar_data = base64.b64encode(file.read()).decode('utf-8')
                    file_extension = file.filename.rsplit('.', 1)[1].lower()
                    user.avatar = f"data:image/{file_extension};base64,{avatar_data}"
        else:
            # 如果是JSON数据
            data = request.json
            if data:
                user.nickname = data.get('nickname', user.nickname)
                user.gender = data.get('gender', user.gender)
                user.college = data.get('college', user.college)

        db.session.commit()
        return jsonify({
            'success': True,
            'message': '资料更新成功',
            'user': user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'})


# API: 用户登出
@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': '已退出登录'})


# ========== 校园记忆API路由 ==========

# API: 获取某个建筑的记忆列表
@app.route('/api/campus/memories/<building>', methods=['GET'])
def get_building_memories(building):
    try:
        # 分页支持
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        memories = CampusMemory.query.filter_by(building=building) \
            .order_by(CampusMemory.created_at.desc()) \
            .paginate(page=page, per_page=per_page, error_out=False)

        # 获取每个记忆的点赞和评论信息
        memory_list = []
        for memory in memories.items:
            memory_dict = memory.to_frontend_dict()

            # 获取点赞数
            like_count = MemoryLike.query.filter_by(memory_id=memory.id).count()
            memory_dict['likes_count'] = like_count

            # 获取评论数
            comment_count = MemoryComment.query.filter_by(memory_id=memory.id).count()
            memory_dict['comments_count'] = comment_count

            # 获取前几条评论
            comments = MemoryComment.query.filter_by(memory_id=memory.id) \
                .order_by(MemoryComment.created_at.asc()) \
                .limit(5).all()
            memory_dict['recent_comments'] = [comment.to_dict() for comment in comments]

            memory_list.append(memory_dict)

        return jsonify({
            'success': True,
            'memories': memory_list,
            'total': memories.total,
            'page': memories.page,
            'pages': memories.pages
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取记忆失败：{str(e)}'})


# API: 提交新记忆（支持图片上传）
@app.route('/api/campus/memories', methods=['POST'])
def submit_memory():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'})

        building = request.form.get('building', '').strip()
        content = request.form.get('content', '').strip()

        if not building:
            return jsonify({'success': False, 'message': '请选择建筑'})

        if not content and 'images' not in request.files:
            return jsonify({'success': False, 'message': '请输入回忆内容或添加图片'})

        # 处理图片上传
        image_files = request.files.getlist('images')
        image_data_list = []

        for image_file in image_files[:3]:  # 最多3张图片
            if image_file and image_file.filename and allowed_file(image_file.filename):
                # 保存图片到uploads目录
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}_{image_file.filename}")
                filepath = os.path.join('uploads', filename)
                image_file.save(filepath)

                # 存储相对路径
                image_data_list.append(f"/uploads/{filename}")

        # 创建新记忆
        new_memory = CampusMemory(
            building=building,
            content=content,
            user_id=user_id,
            images=json.dumps(image_data_list) if image_data_list else '[]'
        )

        db.session.add(new_memory)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '提交成功！',
            'memory': new_memory.to_frontend_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'提交失败：{str(e)}'})


# API: 删除记忆（只能删除自己的）
@app.route('/api/campus/memories/<int:memory_id>', methods=['DELETE'])
def delete_memory(memory_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        memory = CampusMemory.query.get(memory_id)
        if not memory:
            return jsonify({'success': False, 'message': '记忆不存在'})

        # 检查权限：只能删除自己的记忆
        if memory.user_id != user_id:
            return jsonify({'success': False, 'message': '只能删除自己的记忆'})

        db.session.delete(memory)
        db.session.commit()

        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'})


# API: 点赞记忆
@app.route('/api/campus/memories/<int:memory_id>/like', methods=['POST'])
def like_memory(memory_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        memory = CampusMemory.query.get(memory_id)
        if not memory:
            return jsonify({'success': False, 'message': '记忆不存在'})

        # 检查是否已经点赞
        existing_like = MemoryLike.query.filter_by(
            memory_id=memory_id, user_id=user_id
        ).first()

        if existing_like:
            # 取消点赞
            db.session.delete(existing_like)
            memory.likes_count = max(0, memory.likes_count - 1)
            message = '取消点赞成功'
        else:
            # 添加点赞
            new_like = MemoryLike(memory_id=memory_id, user_id=user_id)
            db.session.add(new_like)
            memory.likes_count += 1
            message = '点赞成功'

            # 创建通知（如果不是给自己的记忆点赞）
            if memory.user_id != user_id:
                notification = Notification(
                    user_id=memory.user_id,
                    from_user_id=user_id,
                    type='like_memory',
                    memory_id=memory_id,
                    content=f'{User.nickname} 点赞了你的回忆'
                )
                db.session.add(notification)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': message,
            'likes_count': memory.likes_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败：{str(e)}'})


# API: 添加评论
@app.route('/api/campus/memories/<int:memory_id>/comments', methods=['POST'])
def add_comment(memory_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        data = request.json
        if not data or 'content' not in data:
            return jsonify({'success': False, 'message': '评论内容不能为空'})

        memory = CampusMemory.query.get(memory_id)
        if not memory:
            return jsonify({'success': False, 'message': '记忆不存在'})

        content = data['content'].strip()
        if not content:
            return jsonify({'success': False, 'message': '评论内容不能为空'})

        # 添加评论
        new_comment = MemoryComment(
            memory_id=memory_id,
            user_id=user_id,
            parent_id=data.get('parent_id'),
            content=content
        )

        db.session.add(new_comment)
        memory.comments_count += 1

        # 创建通知（如果不是给自己的记忆评论）
        if memory.user_id != user_id:
            user = User.query.get(user_id)
            notification = Notification(
                user_id=memory.user_id,
                from_user_id=user_id,
                type='comment',
                memory_id=memory_id,
                comment_id=new_comment.id,
                content=f'{user.nickname} 评论了你的回忆：{content[:50]}...'
            )
            db.session.add(notification)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '评论成功',
            'comment': new_comment.to_dict(),
            'comments_count': memory.comments_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'评论失败：{str(e)}'})


# API: 获取记忆的评论
@app.route('/api/campus/memories/<int:memory_id>/comments', methods=['GET'])
def get_memory_comments(memory_id):
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        comments = MemoryComment.query.filter_by(memory_id=memory_id) \
            .order_by(MemoryComment.created_at.asc()) \
            .paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'comments': [comment.to_dict() for comment in comments.items],
            'total': comments.total,
            'page': comments.page,
            'pages': comments.pages
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取评论失败：{str(e)}'})


# API: 获取所有建筑列表（用于统计）
@app.route('/api/campus/buildings', methods=['GET'])
def get_buildings():
    try:
        # 获取有记忆的建筑
        buildings = db.session.query(
            CampusMemory.building,
            db.func.count(CampusMemory.id).label('memory_count')
        ).group_by(CampusMemory.building).all()

        building_list = [{'name': b[0], 'count': b[1]} for b in buildings]

        # 默认建筑列表（即使没有记忆也显示）
        default_buildings = [
            '体育场', '教学实验综合楼', '图书馆', '宿舍楼', '礼堂',
            '学生餐厅', '校园湖', '马克思主义学院', '工程实验楼',
            '理学院', '智能工程与自动化学院', '数字媒体与艺术设计学院',
            '网络空间安全学院', '学生活动中心', '教职工食堂', '天猫超市'
        ]

        # 合并数据
        building_data = []
        for building in default_buildings:
            count = next((b['count'] for b in building_list if b['name'] == building), 0)
            building_data.append({
                'name': building,
                'count': count,
                'has_memories': count > 0
            })

        return jsonify({
            'success': True,
            'buildings': building_data,
            'total_memories': sum(b['count'] for b in building_list)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取建筑列表失败：{str(e)}'})


# API: 获取用户的所有记忆
@app.route('/api/campus/user-memories', methods=['GET'])
def get_user_memories():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        memories = CampusMemory.query.filter_by(user_id=user_id) \
            .order_by(CampusMemory.created_at.desc()) \
            .paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'memories': [memory.to_frontend_dict() for memory in memories.items],
            'total': memories.total,
            'page': memories.page,
            'pages': memories.pages
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取用户记忆失败：{str(e)}'})


# ========== 日记功能API路由 ==========

# API: 获取某个地点的日记列表
@app.route('/api/bupt/diaries/<location>', methods=['GET'])
def get_location_diaries(location):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        diaries = Diary.query.filter_by(location=location, user_id=user_id) \
            .order_by(Diary.created_at.desc()) \
            .paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'diaries': [diary.to_dict() for diary in diaries.items],
            'total': diaries.total,
            'page': diaries.page,
            'pages': diaries.pages
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取日记失败：{str(e)}'})


# API: 创建新日记
@app.route('/api/bupt/diaries', methods=['POST'])
def create_diary():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        data = request.json
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'})

        location = data.get('location', '').strip()
        content = data.get('content', '').strip()

        if not location:
            return jsonify({'success': False, 'message': '请选择地点'})

        if not content:
            return jsonify({'success': False, 'message': '日记内容不能为空'})

        # 创建新日记
        new_diary = Diary(
            location=location,
            content=content,
            user_id=user_id
        )

        db.session.add(new_diary)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '日记保存成功！',
            'diary': new_diary.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'保存日记失败：{str(e)}'})


# API: 获取日记详情
@app.route('/api/bupt/diaries/detail/<int:diary_id>', methods=['GET'])
def get_diary_detail(diary_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        diary = Diary.query.get(diary_id)
        if not diary:
            return jsonify({'success': False, 'message': '日记不存在'})

        # 检查权限：只能查看自己的日记
        if diary.user_id != user_id:
            return jsonify({'success': False, 'message': '只能查看自己的日记'})

        return jsonify({
            'success': True,
            'diary': diary.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取日记详情失败：{str(e)}'})


# API: 删除日记
@app.route('/api/bupt/diaries/<int:diary_id>', methods=['DELETE'])
def delete_diary(diary_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        diary = Diary.query.get(diary_id)
        if not diary:
            return jsonify({'success': False, 'message': '日记不存在'})

        # 检查权限：只能删除自己的日记
        if diary.user_id != user_id:
            return jsonify({'success': False, 'message': '只能删除自己的日记'})

        db.session.delete(diary)
        db.session.commit()

        return jsonify({'success': True, 'message': '日记删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除日记失败：{str(e)}'})


# ========== 通知功能API路由 ==========

# API: 获取用户的通知
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        notifications = Notification.query.filter_by(user_id=user_id) \
            .order_by(Notification.created_at.desc()) \
            .paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'notifications': [notif.to_dict() for notif in notifications.items],
            'total': notifications.total,
            'page': notifications.page,
            'pages': notifications.pages,
            'unread_count': Notification.query.filter_by(user_id=user_id, is_read=False).count()
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取通知失败：{str(e)}'})


# API: 标记通知为已读
@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({'success': False, 'message': '通知不存在'})

        # 检查权限：只能操作自己的通知
        if notification.user_id != user_id:
            return jsonify({'success': False, 'message': '权限不足'})

        notification.is_read = True
        db.session.commit()

        return jsonify({'success': True, 'message': '已标记为已读'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败：{str(e)}'})


# API: 清空所有通知
@app.route('/api/notifications/clear', methods=['POST'])
def clear_notifications():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '请先登录'})

        # 删除该用户的所有通知
        Notification.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        return jsonify({'success': True, 'message': '已清空所有通知'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'清空失败：{str(e)}'})


# ========== 文件服务 ==========

# 提供上传的文件访问
@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    return send_from_directory('uploads', filename)


# 健康检查
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})


# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': '请求的资源不存在'}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'success': False, 'message': '服务器内部错误'}), 500


if __name__ == '__main__':
    with app.app_context():
        # 创建数据库表（如果不存在）
        db.create_all()
    app.run(host='0.0.0.0', port=8080, debug=True)

# 在文件末尾修改
if __name__ == '__main__':
    # 创建必要目录
    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    # 初始化数据库
    with app.app_context():
        db.create_all()

    # 使用Render提供的端口
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)  # 生产环境关闭debug