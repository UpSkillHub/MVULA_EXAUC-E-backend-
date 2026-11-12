from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.permission import Permission
from app.models.user import User
from app.models.document import Document
from flask_jwt_extended import jwt_required, get_jwt_identity

permission_bp = Blueprint(
    "permissions",
    __name__,
    url_prefix="/permissions"
)

def get_current_user():
    user_id = get_jwt_identity()
    return db.session.get(User, int(user_id))

@permission_bp.route("/", methods=["POST"])
@jwt_required()
def assign_permission():
    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role not in ["admin", "superadmin"]:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON data is required"}), 400

    user = User.query.get(data.get("user_id"))
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.role == "superadmin":
        return jsonify({"error": "Permissions cannot be assigned to superadmins"}), 400

    document = Document.query.get(data.get("document_id"))
    if not document:
        return jsonify({"error": "Document not found"}), 404

    if current_user.role == "admin":
        if current_user.organization_id != document.organization_id:
            return jsonify({"error": "Access denied"}), 403

        if user.organization_id != document.organization_id:
            return jsonify({"error": "User must belong to your organization"}), 403

    existing_permission = Permission.query.filter_by(
        user_id=user.id,
        document_id=document.id
    ).first()

    if existing_permission:
        return jsonify({"error": "Permission already exists"}), 409

    permission = Permission(
        user_id=user.id,
        document_id=document.id,
        can_view=data.get("can_view", False),
        can_download=data.get("can_download", False),
        can_edit=data.get("can_edit", False),
        can_delete=data.get("can_delete", False)
    )

    db.session.add(permission)
    db.session.commit()

    return jsonify({
        "id": permission.id,
        "user_id": permission.user_id,
        "document_id": permission.document_id,
        "can_view": permission.can_view,
        "can_download": permission.can_download,
        "can_edit": permission.can_edit,
        "can_delete": permission.can_delete,
        "message": "Permission created successfully"
    }), 201

@permission_bp.route("/", methods=["GET"])
@jwt_required()
def get_permissions():
    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role not in ["admin", "superadmin"]:
        return jsonify({"error": "Access denied"}), 403

    query = Permission.query.join(Document)

    if current_user.role == "admin":
        query = query.filter(
            Document.organization_id == current_user.organization_id
        )

    permissions = query.all()

    return jsonify([
        {
            "id": permission.id,
            "user_id": permission.user_id,
            "document_id": permission.document_id,
            "can_view": permission.can_view,
            "can_download": permission.can_download,
            "can_edit": permission.can_edit,
            "can_delete": permission.can_delete
        }
        for permission in permissions
    ]), 200

@permission_bp.route("/<int:permission_id>", methods=["GET"])
@jwt_required()
def get_permission(permission_id):
    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    permission = Permission.query.get(permission_id)

    if not permission:
        return jsonify({"error": "Permission not found"}), 404

    document = Document.query.get(permission.document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    if current_user.role == "admin":
        if current_user.organization_id != document.organization_id:
            return jsonify({"error": "Access denied"}), 403

    if current_user.role not in ["admin", "superadmin"]:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({
        "id": permission.id,
        "user_id": permission.user_id,
        "document_id": permission.document_id,
        "can_view": permission.can_view,
        "can_download": permission.can_download,
        "can_edit": permission.can_edit,
        "can_delete": permission.can_delete
    }), 200

@permission_bp.route("/<int:permission_id>", methods=["PUT"])
@jwt_required()
def update_permission(permission_id):
    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role not in ["admin", "superadmin"]:
        return jsonify({"error": "Access denied"}), 403

    permission = Permission.query.get(permission_id)

    if not permission:
        return jsonify({"error": "Permission not found"}), 404

    document = Document.query.get(permission.document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    if current_user.role == "admin":
        if current_user.organization_id != document.organization_id:
            return jsonify({"error": "Access denied"}), 403

    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON data is required"}), 400

    permission.can_view = data.get("can_view", permission.can_view)
    permission.can_download = data.get("can_download", permission.can_download)
    permission.can_edit = data.get("can_edit", permission.can_edit)
    permission.can_delete = data.get("can_delete", permission.can_delete)

    db.session.commit()

    return jsonify({
        "message": "Permission updated successfully",
        "id": permission.id,
        "user_id": permission.user_id,
        "document_id": permission.document_id,
        "can_view": permission.can_view,
        "can_download": permission.can_download,
        "can_edit": permission.can_edit,
        "can_delete": permission.can_delete
    }), 200

@permission_bp.route("/<int:permission_id>", methods=["DELETE"])
@jwt_required()
def delete_permission(permission_id):
    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role not in ["admin", "superadmin"]:
        return jsonify({"error": "Access denied"}), 403

    permission = Permission.query.get(permission_id)

    if not permission:
        return jsonify({"error": "Permission not found"}), 404

    document = Document.query.get(permission.document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    if current_user.role == "admin":
        if current_user.organization_id != document.organization_id:
            return jsonify({"error": "Access denied"}), 403

    db.session.delete(permission)
    db.session.commit()

    return jsonify({
        "message": "Permission deleted successfully"
    }), 200