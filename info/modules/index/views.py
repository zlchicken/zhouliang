from info.models import User, News, Category
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import index_blu
from flask import render_template, session, jsonify, current_app, request, g
from info import constants


@index_blu.route("/")
@user_login_data
def index():

    # 查询点击排行数据
    try:
        hot_news = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")
    # 查询新闻分类
    try:
        news_class = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")
    # 查询用户登陆状态
    user = g.user
    data = {
        "user": user,
        "hot_news": hot_news,
        "news_class": news_class
    }
    return render_template("news/index.html", data=data)
