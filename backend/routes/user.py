from flask import Blueprint, jsonify
from flask_login import login_required, current_user


bp = Blueprint('user', __name__)


@bp.route('/me')
@login_required
def me():
    return jsonify({
'id': current_user.id,
'username': current_user.username,
'role': getattr(current_user, 'role', 'student')
})