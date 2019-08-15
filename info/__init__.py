import logging
from logging.handlers import RotatingFileHandler
from flask import Flask

# 可以用来指定session保存位置
from flask_wtf import CSRFProtect
from flask_session import  Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import generate_csrf
from redis import StrictRedis

from config import config


# 初始化数据库



db = SQLAlchemy()

# 变量注释,指定变量类型(使用全局变量无法智能提示时)
redis_store = None




def setup_log(config_name):
    # 设置日志的记录等级
    logging.basicConfig(level=config[config_name].LOG_LEVEL)
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


def create_app(config_name):
    # 配置日志,并且传入配置名字，获取指定配置所对应的日志等级
    setup_log(config_name)
    # 创建Flask对象'
    app = Flask(__name__)
    # 加载配置
    app.config.from_object(config[config_name])
    # 通过app初始化
    db.init_app(app)
    # 初始化 redis 存储对象
    global redis_store
    redis_store = StrictRedis(host=config[config_name].REDIS_HOST, port=config[config_name].REDIS_PORT, decode_responses=True)
    # 开启当前项目 CSRF 保护，只做服务器验证功能
    @app.after_request
    def after_request(response):
        # 调用函数生成 csrf_token
        csrf_token = generate_csrf()
        # 通过 cookie 将值传给前端
        response.set_cookie("csrf_token", csrf_token)
        return response
    # CSRFProtect(app)
    # 设置session保存指定位置
    Session(app)
    # 注册蓝图
    from info.modules.index import index_blu
    app.register_blueprint(index_blu)

    from info.modules.passport import passport_blu
    app.register_blueprint(passport_blu)

    from info.modules.news import news_blu
    app.register_blueprint(news_blu)

    from info.modules.profile import profile_blu
    app.register_blueprint(profile_blu)

    # 注册自定义过滤器
    from info.utils.common import do_index_class
    app.add_template_filter(do_index_class, "indexClass")
    return app
