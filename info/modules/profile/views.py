from info import db
from info.models import User
from info.utils.common import user_login_data
from info.utils.response_code import RET
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
