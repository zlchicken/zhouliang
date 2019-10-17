from flask import request, current_app, jsonify, render_template, g
from sqlalchemy import and_

from info import constants, db
from info.models import News, Category, Comment, CommentLike, User
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import news_blu


@news_blu.route('/news_list')
def news_list():
    cid = request.args.get('cid', '1')
    page = request.args.get('page', '1')
    per_page = request.args.get('per_page', constants.HOME_PAGE_MAX_NEWS)
    # 2. 校验参数
    try:
        page = int(page)
        cid = int(cid)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.eror(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    # 默认选择最新数据分类
    filters = []
    if cid != 1:  # 查询的不是最新的数据
        # 需要添加条件
        filters.append(News.category_id == cid)
    filters.append(News.status == 0)
    # 3. 查询数据
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据查询错误')
    # 取到当前页的数据
    news_mode_list = paginate.items
    total_page = paginate.pages
    current_page = paginate.page
    # 将模型对象列表转成字典列表
    news_dict_list = []
    for new in news_mode_list:
        news_dict_list.append(new.to_basic_dict())
    # 返回数据
    data = {
        'total_page': total_page,
        'current_page': current_page,
        'news_dict_list': news_dict_list
    }
    return jsonify(errno=RET.OK, errmsg='OK', data=data)


@news_blu.route('/<int:news_id>')
@user_login_data
def news_detail(news_id):

    # 查询点击排行数据
    try:
        hot_news = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")
    # 查询用户登陆状态
    user = g.user
    # 查询新闻数据
    try:
        new_id = News.query.filter_by(id=news_id).first()
        new_id.comments_count = Comment.query.filter_by(news_id=news_id).count()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")
    # 当前登录用户是否关注当前新闻作者
    is_followed = False
    # 判断用户是否收藏过该新闻
    print()
    if new_id.user and user:
        if new_id.user in user.followed:
            is_followed = True
    # 校验报404错误
    if not new_id:
        return render_template("static/../../templates/news/404.html")
    # 进入详情页后要更新新闻的点击次数
    try:
        new_id.clicks += 1
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="增加失败")
    # 判断是否收藏该新闻，默认值为 false
    is_collected = False
    if user:
        news_lists = user.collection_news.all()
        if new_id in news_lists:
            is_collected = True
    comments = Comment.query.filter_by(news_id=news_id).order_by(Comment.create_time.desc()).all()
    comment_like_ids = []
    if user:
        # 评论信息查询
        # 查询当前新闻所有评论哪些被当前用户点赞
        for comment in comments:
            commentlike_users = CommentLike.query.filter(and_(CommentLike.comment_id == comment.id, CommentLike.user_id == user.id)).all()
            # 取出所有被点赞评论ID
            for commentlike_user in commentlike_users:
                comment_like_ids.append(commentlike_user.comment_id)
    # 遍历评论id,将评论属性赋值
    comment_dict_list = []
    for comment in comments:
        comment_dict = comment.to_dict()
        # 为评论增加'is_like'字段,判断是否评论
        comment_dict['is_like'] = False
        # 判断用户是否在点赞评论里
        if comment.id in comment_like_ids:
            comment_dict["is_like"] = True
        comment_dict_list.append(comment_dict)
    # 返回数据
    data = {
        'is_followed': is_followed,
        "news": new_id.to_dict(),
        "user": user,
        "hot_news": hot_news,
        "is_collected": is_collected,
        "comments": comment_dict_list,
        "news_id": news_id,
    }
    return render_template('detail/detail.html', data=data)


@news_blu.route("/news_collect", methods=['POST'])
@user_login_data
def news_collect():
    """新闻收藏"""

    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 获取参数
    news_id = request.json.get("news_id")
    action = request.json.get("action")
    # 判断参数
    if not all ([news_id,action]):
        return jsonify(errno=RET.NODATA, errmsg="参数不完整")
    # action在不在指定的两个值：'collect', 'cancel_collect'内
    if action not in ["collect", "cancel_collect"]:
        return jsonify(errno=RET.DATAERR, errmsg="参数不正确")
    # 查询新闻,并判断新闻是否存在
    try:
        new = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")
    if not new:
        return jsonify(errno=RET.NODATA, errmsg="数据不存在")
    # 收藏/取消收藏
    if action == "cancel_collect":
        # 取消收藏
        # if user:
        user.collection_news.remove(new)
    else:
        # 收藏
        # if user:
        user.collection_news.append(new)
    return jsonify(errno=RET.OK, errmsg="收藏成功")


@news_blu.route('/news_comment', methods=["POST"])
@user_login_data
def add_news_comment():
    """添加评论"""

    # 用户是否登陆
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 获取参数json格式
    # "news_id": news_id,
    # "comment": news_comment
    news_id = int(request.json.get("news_id"))
    content = request.json.get("comment")
    parent_id = request.json.get("parent_id", "")
    # 判断参数是否正确
    if not all([news_id, content]):
        return jsonify(errno=RET.NODATA, errmsg="参数不完整")
    # 查询新闻是否存在并校验
    try:
        new = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")
    if not new:
        return jsonify(errno=RET.NODATA, errmsg="数据不存在")
    # 初始化评论模型，保存数据

    try:
        parent = Comment.query.filter_by(id=parent_id).first()
        com = Comment()
        com.news_id = news_id
        com.user_id = user.id
        com.content = content
        com.parent_id = parent_id
        com.parent = parent
        db.session.add(com)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库错误")
    # 配置文件设置了自动提交,自动提交要在return返回结果以后才执行commit命令,如果有回复
    # 评论,先拿到回复评论id,在手动commit,否则无法获取回复评论内容
    # 返回响应
    # data = {
    #     "user": user.to_dict(),
    #     "content": news_ids.content,
    #     "create_time": news_ids.create_time,
    #     "parent": parent.to_dict() if parent else None,
    #     "news_id": news_id,
    #     "id": news_ids.id
    #     # "comments": [news_idss.to_dict() for news_idss in news_ids]
    # }

    return jsonify(errno=RET.OK,data=com.to_dict())


@news_blu.route('/comment_like', methods=["POST"])
@user_login_data
def comment_like():
    """
    评论点赞
    :return:
    """
    # 用户是否登陆
    user = g.user
    if not user:
        return jsonify(errno=RET.SERVERERR,errmsg="用户未登录")
    # 取到请求参数
    comment_id = request.json.get("comment_id")
    action = request.json.get("action")
    # 判断参数
    if not all([comment_id, action]):
        return jsonify(errno=RET.NODATA, errmsg="参数不完整")
    # 获取到要被点赞的评论模型
    try:
        comment = Comment.query.filter_by(id=comment_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")

# action的状态,如果点赞,则查询后将用户id和评论id添加到数据库
    if action == "add":
        try:
            commentlike = CommentLike(comment_id=comment_id, user_id=user.id)
            db.session.add(commentlike)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="点赞失败")
        # 点赞评论
        try:
            comment.like_count += 1
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="修改失败")
        # 更新点赞次数

        # 取消点赞评论,查询数据库,如果以点赞,则删除点赞信息
    elif action == "remove":
        try:
            comments = CommentLike.query.filter(and_(CommentLike.comment_id == comment_id, CommentLike.user_id == user.id)).first()
            db.session.delete(comments)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="修改失败")
        # 更新点赞次数
        try:
            comment.like_count -= 1
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="修改失败")
    return jsonify(errno=RET.OK, errmsg="点赞成功")


@news_blu.route('/followed_user', methods=["POST"])
@user_login_data
def followed_user():
    """关注或者取消关注用户"""

    # 获取自己登录信息
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="未登录")

    # 获取参数
    user_id = request.json.get("user_id")
    action = request.json.get("action")

    # 判断参数
    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ("follow", "unfollow"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 获取要被关注的用户
    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    if not other:
        return jsonify(errno=RET.NODATA, errmsg="未查询到数据")

    if other.id == user.id:
        return jsonify(errno=RET.PARAMERR, errmsg="请勿关注自己")

    # 根据要执行的操作去修改对应的数据
    if action == "follow":
        if other not in user.followed:
            # 当前用户的关注列表添加一个值
            user.followed.append(other)
        else:
            return jsonify(errno=RET.DATAEXIST, errmsg="当前用户已被关注")
    else:
        # 取消关注
        if other in user.followed:
            user.followed.remove(other)
        else:
            return jsonify(errno=RET.DATAEXIST, errmsg="当前用户未被关注")

    return jsonify(errno=RET.OK, errmsg="操作成功")
