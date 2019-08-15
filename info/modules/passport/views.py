import re
import random
from flask import request, current_app, abort, make_response, jsonify, session
from info import redis_store, constants, db
from info.models import User
from info.modules.passport import passport_blu
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET, error_map


@passport_blu.route('/image_code')
def get_image_code():
    # 生成图片验证码
    # 1. 获取参数
    image_Code = request.args.get('image_Code')
    # 2. 校验参数
    if not image_Code:
        abort(403)
    # 3. 生成图片验证码
    name, text, image_data = captcha.generate_captcha()
    # 4. 保存图片验证码
    try:
        redis_store.setex("img_%s" % image_Code, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        print(text)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="save image code failed ")
    # 5.返回图片验证码
    resp = make_response(image_data)
    resp.headers["Content-Type"] = "image/jpg"
    return resp


@passport_blu.route('/sms_code', methods=['POST'])
def send_sms_code():
    print(1111)
    # 1.将前端参数转为字典
    mobile = request.json.get("mobile")
    image_code = request.json.get("image_code")
    image_code_id = request.json.get("image_code_id")
    # 2. 校验参数(参数是否符合规则，判断是否有值)
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg=error_map[RET.PARAMERR])
    if not re.match(r"1[35678]\d{9}$", mobile):
    # if not re.match("\d", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="mobile is not required")
    # 3. 先从redis中取出真实的验证码内容
    try:
        redis_image_code = redis_store.get("img_%s" % image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="image code failed")
    # 4. 与用户的验证码内容进行对比，如果对比不一致，那么返回验证码输入错误
    if redis_image_code is None:
        return jsonify(errno=RET.NODATA, errmsg="image code id is null")
    if image_code.lower() != redis_image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg=error_map.DATAERR)
    # 5. 如果一致，生成短信验证码的内容(随机数据)
    # code = "".join([str(random.randint(0, 9)) for _ in range(6)])
    code = random.randint(100000, 999999)
    # 6. 发送短信验证码
    print("sms_code{}".format(code))
    # 保存验证码内容到redis
    try:
        redis_store.setex("sms_code_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="save sms code failed")
    # 7. 告知发送结果
    if not code is None:
        return jsonify(errno=RET.OK, errmsg="send OK!")


@passport_blu.route("/register", methods=["POST"])
def register():
    # 注册
    # 1. 获取参数和判断是否有值
    mobile = request.json.get("mobile")
    smscode = request.json.get("smscode")
    password = request.json.get("password")
    if not all([mobile, smscode, password]):
        return jsonify(errno=RET.PARAMERR, errmsg=error_map[RET.PARAMERR])
    # 2. 从redis中获取指定手机号对应的短信验证码的
    try:
        redis_sms_code = redis_store.get("sms_code_%s" % mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="select sms code failed")
    # 3. 校验验证码
    if redis_sms_code != smscode:
        return jsonify(errno=RET.PARAMERR, errmsg=error_map[RET.PARAMERR])
    # 4. 初始化 user 模型，并设置数据并添加到数据库
    print(mobile,smscode,password)
    try:
        user = User()
        user.mobile = mobile
        user.password = password
        user.nick_name = mobile
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="add datas failed")
    # 5. 保存用户登录状态
    session["nick_name"] = mobile
    session["mobile"] = mobile
    session["user_id"] = user.id
    # 6. 返回注册结果
    return jsonify(errno=RET.OK, errmsg="register is OK!")


@passport_blu.route('/login', methods=["POST"])
def login():
    # 1. 获取参数和判断是否有值
    mobile = request.json.get("mobile")
    password = request.json.get("password")
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg=error_map[RET.PARAMERR])
    # 2. 从数据库查询出指定的用户
    try:
        user = User.query.filter_by(mobile=mobile).first()
        mobile_db = user.mobile
        print(mobile_db)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg=error_map[RET.DBERR])
    if not mobile_db:
        return jsonify(errno=RET.DBERR, errmsg="user is not exit")
    # 3. 校验密码
    try:
        # password_db = user.password_hash
        password_db = user.check_password(password)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg=error_map[RET.DBERR])
    if not password_db:
        return jsonify(errno=RET.PWDERR, errmsg=error_map[RET.PWDERR])
    # 4. 保存用户登录状态
    session["nick_name"] = mobile
    session["mobile"] = mobile
    session["user_id"] = user.id
    # 5. 登录成功返回
    return jsonify(errno=RET.OK, errmsg=error_map[RET.OK])


@passport_blu.route("/logout", methods=['POST'])
def logout():
    session.pop("user_id")
    return jsonify(errno=RET.OK, errmsg=error_map[RET.OK])
