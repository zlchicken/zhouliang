import os

from info import db, constants
from info.models import User, Category, News
from info.utils.common import user_login_data
from info.utils.response_code import RET, error_map
from . import profile_blu
from flask import render_template, g, redirect, request, current_app, jsonify, abort


@profile_blu.route('/info')
@user_login_data
def user_info():
    user = g.user
    # 如果用户登陆则进入个人中心
    if not user:
        return redirect("/")
    # 如果没有登陆,跳转主页
    # 返回用户数据
    data = {
        "user": user.to_dict()
    }
    return render_template("news/user.html", data=data)


@profile_blu.route('/base_info', methods=["POST", "GET"])
@user_login_data
def base_info():
    """
    用户基本信息
    :return:
    """
    if request.method == "GET":
        return render_template('news/user_base_info.html', data={"user": g.user.to_dict()})

    # 修改用户数据
    nick_name = request.json.get("nick_name")
    signature = request.json.get("signature")
    gender = request.json.get("gender")
    # if gender == "男":
    #     gender = "MAN"
    # else:
    #     gender = "WOMAN"
    try:
        user = g.user
        user.nick_name = nick_name
        user.signature = signature
        user.gender = gender
        # db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="修改失败")
    return jsonify(errno=RET.OK, errmsg="成功")


@profile_blu.route('/pass_info', methods=["GET", "POST"])
@user_login_data
def pass_info():
    if request.method == "GET":
        return render_template('news/user_pass_info.html')
    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")
    new_password2 = request.json.get("new_password2")
    if not all([old_password, new_password, new_password2]):
        return jsonify(err=RET.DATAERR, errmsg="参数不完整")
    if new_password != new_password2:
        return jsonify(RET.DATAERR, errmsg="密码不一致")
    # 3. 校验密码
    try:
        user = g.user
        # password_db = user.password_hash
        password_db = user.check_password(old_password)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg=error_map[RET.DBERR])
    if not password_db:
        return jsonify(errno=RET.PWDERR, errmsg=error_map[RET.PWDERR])
    try:
        user.password = new_password
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg=error_map[RET.DBERR])
    return jsonify(errno=RET.OK, errmsg="修改成功")


@profile_blu.route('/collection')
@user_login_data
def user_collection():
    # 获取参数
    p = int(request.args.get("p", 1))
    user = g.user

    paginate = user.collection_news.paginate(p, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)
    paginates = paginate.items
    page = paginate.page
    pages = paginate.pages
    paginate_lists = [paginate_list.to_dict() for paginate_list in paginates]
    data = {
        "collections": paginate_lists,
        "current_page": page,
        "total_page": pages,
    }
    return render_template('news/user_collection.html', data=data)


@profile_blu.route('/news_release', methods=["GET", "POST"])
@user_login_data
def news_release():
    if request.method == "GET":
        categorys = Category.query.all()
        category = [category.to_dict() for category in categorys]
        for i in category:
            if i["name"] == "最新":
                category.remove(i)
        data = {
            "categories": category,
        }
        return render_template("news/user_news_release.html", data=data)
    user = g.user
    title = request.form.get("title")
    category_id = request.form.get("category_id")
    digest = request.form.get("digest")
    # index_image = request.form.get("index_image")
    content = request.form.get("content")
    # content = request.form["content"]
    source = request.form.get("source", "个人")
    if not all([user, title, category_id, digest, content, source]):
        return jsonify(errno=RET.DATAERR, errmsg="参数不全")
    # print(digest, content)
    try:
        news = News()
        news.digest = digest
        news.source = source
        news.content = content
        news.category_id = category_id
        news.title = title
        news.status = 1
        news.user_id = user.id
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="添加失败")
    return jsonify(errno=RET.OK, errmsg='ok')


@profile_blu.route('/news_list')
@user_login_data
def user_news_list():
    user = g.user
    if not user:
        return redirect('/')
    try:
        news = News.query.filter(News.user_id == user.id).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")
    # news_list = [new.to_dict() for new in news]
    # News.query.filter_by(user_id=user.id).all()
    return render_template('news/user_news_list.html', data={"news_list": news})


@profile_blu.route('/user_follow')
@user_login_data
def user_follow():
    # 获取页数
    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user

    follows = []
    current_page = 1
    total_page = 1
    try:
        paginate = user.followed.paginate(p, constants.USER_FOLLOWED_MAX_COUNT, False)
        # 获取当前页数据
        follows = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    user_dict_li = []

    for follow_user in follows:
        user_dict_li.append(follow_user.to_dict())
    data = {"users": user_dict_li, "total_page": total_page, "current_page": current_page}
    return render_template('news/user_follow.html', data=data)


@profile_blu.route('/other_info')
@user_login_data
def other_info():
    user = g.user

    # 去查询其他人的用户信息
    other_id = request.args.get("user_id")
    if not other_id:
        abort(404)

    # 查询指定id的用户信息
    other = None
    try:
        other = User.query.get(other_id)
    except Exception as e:
        current_app.logger.error(e)

    if not other:
        abort(404)

    # 判断当前登录用户是否关注过该用户
    is_followed = False
    if other and user:
        if other in user.followed:
            is_followed = True

    data = {
        "is_followed": is_followed,
        "user": g.user.to_dict() if g.user else None,
        "other_info": other.to_dict()
    }
    return render_template('news/other.html', data=data)


@profile_blu.route('/other_news_list')
def other_news_list():
    """返回指定用户的发布的新闻"""
    # 1. 取参数
    other_id = request.args.get("user_id")
    page = request.args.get("p", 1)
    # 2. 判断参数
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        other = User.query.get(other_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    if not other:
        return jsonify(errno=RET.NODATA, errmsg="当前用户不存在")
    try:
        paginate = other.news_list.paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    news_dict_list = []
    for news_item in news_li:
        news_dict_list.append(news_item.to_basic_dict())

    data = {
        "news_list": news_dict_list,
        "total_page": total_page,
        "current_page": current_page
    }
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


@profile_blu.route('/pic_info', methods=["GET", "POST"])
@user_login_data
def pic_info():
    # 如果是GET请求,返回用户数据
    if request.method == "GET":
        user = g.user
        return render_template("news/user_pic_info.html",user=user)
    else:
        avatar = request.files.get('avatar')
        from uuid import uuid4
        filename = str(uuid4()).replace("-","")+".jpg"
        filepath = os.path.join(constants.MEDIA_USER_PATH,filename)
        spath = os.path.join("/static/media/user",filename)
        os.path.basename(spath)
        relpath = os.path.join(constants.MEDIA_USER_PATH,os.path.basename(spath))
        os.remove(relpath)
        print(avatar)
        avatar.save(filepath)
        return jsonify(errno=500,errmsg="数据以传入")
    # 如果是POST请求表示修改头像
    # 1. 获取到上传的图片

    # 2. 上传头像

        # 使用自已封装的storage方法去进行图片上传

    # 3. 保存头像地址
    # 拼接url并返回数据
    # return "hello world"
