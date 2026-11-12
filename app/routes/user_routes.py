from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.user import User
from app.models.organization import Organization
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import jwt_required, get_jwt_identity

user_bp = Blueprint("users", __name__, url_prefix="/users")

def get_current_user():
    user_id = get_jwt_identity()
    return db.session.get(User, int(user_id))


@user_bp.route("/register", methods=["POST"])
def create_user():
    data = request.get_json()

    if not data or not all(data.get(field) for field in
                           ["name", "email", "password"]):
        return jsonify({"error": "All fields are required"}), 400

    organization_id = data.get("organization_id")

    if not organization_id:
        return jsonify({"error": "Organization ID is required"}), 400

    if not db.session.get(Organization, organization_id):
        return jsonify({"error": "Organization not found"}), 404

    user = User(
        organization_id=organization_id,
        name=data["name"],
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
        role="member"
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "A user with this email already exists"
        }), 409

    return jsonify({
        "id": user.id,
        "organization_id": user.organization_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at.isoformat(),
        "message": "User created successfully"
    }), 201


@user_bp.route("/<int:user_id>/role", methods=["PUT"])
@jwt_required()
def change_user_role(user_id):
    data = request.get_json()

    if not data or not data.get("role"):
        return jsonify({"error": "Role is required"}), 400

    new_role = data["role"]

    if new_role not in ["member", "admin", "superadmin"]:
        return jsonify({"error": "Invalid role"}), 400

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    target_user = db.session.get(User, user_id)

    if not target_user:
        return jsonify({"error": "Target user not found"}), 404

    if current_user.role == "superadmin":

        if new_role == "superadmin":
            target_user.organization_id = None

        elif target_user.organization_id is None:
            return jsonify({
                "error": "User must belong to an organization"
            }), 400

    elif current_user.role == "admin":

        if new_role != "admin":
            return jsonify({
                "error": "Admins can only promote members to admin"
            }), 403

        if current_user.organization_id != target_user.organization_id:
            return jsonify({"error": "Access denied"}), 403

        if target_user.role != "member":
            return jsonify({
                "error": "Only members can be promoted"
            }), 400

    else:
        return jsonify({"error": "Access denied"}), 403

    target_user.role = new_role
    db.session.commit()

    return jsonify({
        "id": target_user.id,
        "organization_id": target_user.organization_id,
        "name": target_user.name,
        "email": target_user.email,
        "role": target_user.role,
        "message": "User role updated successfully"
    }), 200


@user_bp.route("/", methods=["GET"])
@jwt_required()
def get_users():
    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role == "superadmin":
        users = User.query.all()

    elif current_user.role == "admin":
        users = User.query.filter_by(
            organization_id=current_user.organization_id
        ).all()

    else:
        users = [current_user]

    return jsonify([
        {
            "id": user.id,
            "organization_id": user.organization_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat()
        }
        for user in users
    ]), 200

@user_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role == "superadmin":
        pass
    elif current_user.role == "admin":
        if current_user.organization_id != user.organization_id:
            return jsonify({"error": "Access denied"}), 403
    else:
        if current_user.id != user.id:
            return jsonify({"error": "Access denied"}), 403

    return jsonify({
        "id": user.id,
        "organization_id": user.organization_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at.isoformat()
    }), 200

@user_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role == "superadmin":
        pass
    elif current_user.role == "admin":
        if current_user.organization_id != user.organization_id:
            return jsonify({"error": "Access denied"}), 403
    else:
        if current_user.id != user.id:
            return jsonify({"error": "Access denied"}), 403

    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    if "name" in data:
        user.name = data["name"]

    if "email" in data:
        user.email = data["email"]

    db.session.commit()

    return jsonify({
        "id": user.id,
        "organization_id": user.organization_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at.isoformat(),
        "message": "User updated successfully"
    }), 200

@user_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role == "superadmin":
        pass
    elif current_user.role == "admin":
        if current_user.organization_id != user.organization_id:
            return jsonify({"error": "Access denied"}), 403

        if user.role != "member":
            return jsonify({
                "error": "Admins can only delete members"
            }), 403
    else:
        return jsonify({"error": "Access denied"}), 403

    db.session.delete(user)
    db.session.commit()

    return jsonify({
        "message": "User deleted successfully"
    }), 200