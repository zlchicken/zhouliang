from info import db, constants
from info.models import User, Category
from info.utils.common import user_login_data
from info.utils.response_code import RET, error_map
from . import profile_blu
from flask import render_template, g, redirect, request, current_app, jsonify


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
    print("*"*50)
    print(gender)
    print("*" * 50)
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
    print(old_password, new_password, new_password2)
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
            "category": category,
        }
        return render_template("news/user_news_release.html", data=data)
