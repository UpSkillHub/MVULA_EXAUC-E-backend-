from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.organization import Organization
from app.models.user import User
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

organization_bp = Blueprint(
    "organizations", __name__, url_prefix="/organizations"
)

def get_current_user():
    user_id = get_jwt_identity()
    return db.session.get(User, int(user_id))


@organization_bp.route("/", methods=["POST"])
@jwt_required()
def create_organization():
    data = request.get_json()

    current_user = get_current_user()

    if not current_user or current_user.role != "superadmin":
        return jsonify({"error": "Superadmin access required"}), 403

    if not data or not data.get("name") or not data.get("email"):
        return jsonify({
            "error": "Name and email are required"
        }), 400

    organization = Organization(
        name=data["name"],
        email=data["email"]
    )

    db.session.add(organization)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "An organization with this email already exists"}), 409

    return jsonify({
        "id": organization.id,
        "name": organization.name,
        "email": organization.email,
        "created_at": organization.created_at.isoformat(),
        "message": "Organization created successfully"
    }), 201

@organization_bp.route("/", methods=["GET"])
@jwt_required()
def get_organizations():
    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role == "superadmin":
        organizations = Organization.query.all()
    else:
        organizations = Organization.query.filter_by(
            id=current_user.organization_id
        ).all()

    return jsonify([
        {
            "id": org.id,
            "name": org.name,
            "email": org.email,
            "created_at": org.created_at.isoformat()
        }
        for org in organizations
    ]), 200

@organization_bp.route("/<int:org_id>", methods=["GET"])
@jwt_required()
def get_organization(org_id):
    organization = db.session.get(Organization, org_id)

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role != "superadmin" and current_user.organization_id != org_id:
        return jsonify({"error": "Access denied"}), 403

    if not organization:
        return jsonify({"error": "Organization not found"}), 404

    return jsonify({
        "id": organization.id,
        "name": organization.name,
        "email": organization.email,
        "created_at": organization.created_at.isoformat()
    }), 200

@organization_bp.route("/<int:org_id>", methods=["PUT"])
@jwt_required()
def update_organization(org_id):
    organization = db.session.get(Organization, org_id)

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role not in ["admin", "superadmin"]:
        return jsonify({"error": "Admin access required"}), 403

    if current_user.role == "admin" and current_user.organization_id != org_id:
        return jsonify({"error": "Access denied"}), 403

    if not organization:
        return jsonify({"error": "Organization not found"}), 404

    data = request.get_json()

    if not data or not data.get("name") or not data.get("email"):
        return jsonify({"error": "Name and email are required"}), 400

    organization.name = data["name"]
    organization.email = data["email"]

    db.session.commit()

    return jsonify({
        "id": organization.id,
        "name": organization.name,
        "email": organization.email,
        "created_at": organization.created_at.isoformat(),
        "message": "Organization updated successfully"
    }), 200

@organization_bp.route("/<int:org_id>", methods=["DELETE"])
@jwt_required()
def delete_organization(org_id):
    organization = db.session.get(Organization, org_id)

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role not in ["admin", "superadmin"]:
        return jsonify({"error": "Admin access required"}), 403

    if current_user.role == "admin" and current_user.organization_id != org_id:
        return jsonify({"error": "Access denied"}), 403

    if not organization:
        return jsonify({"error": "Organization not found"}), 404

    db.session.delete(organization)
    db.session.commit()

    return jsonify({
        "message": "Organization deleted successfully"
    }), 200