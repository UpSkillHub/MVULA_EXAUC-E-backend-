from flask import Blueprint, request, jsonify, current_app, send_file
from app.extensions import db
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User
from app.models.permission import Permission
import os
import uuid
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity

document_bp = Blueprint(
    "documents", __name__, url_prefix="/documents"
)

def get_current_user():
    user_id = get_jwt_identity()
    return db.session.get(User, int(user_id))

ALLOWED_EXTENSIONS = {"pdf", "txt", "png", "jpg", "jpeg", "zip"}

@document_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():
    file = request.files.get("file")
    organization_id = request.form.get("organization_id", type=int)
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "User not found"}), 404
    uploaded_by = current_user.id

    if not file or not file.filename:
        return jsonify({"error": "A file is required"}), 400

    if not organization_id:
        return jsonify({"error": "Organization ID is required"}), 400

    organization = Organization.query.get(organization_id)
    if not organization:
        return jsonify({"error": "Organization not found"}), 404

    if current_user.role == "superadmin":
        pass
    elif current_user.organization_id != organization_id:
        return jsonify({"error": "Access denied"}), 403

    original_name = secure_filename(file.filename)

    if "." not in original_name:
        return jsonify({"error": "Invalid filename"}), 400

    extension = original_name.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "File type not allowed"}), 400

    duplicate = Document.query.filter_by(
        organization_id=organization_id,
        name=original_name
    ).first()

    if duplicate:
        return jsonify({
            "error": "A document with this filename already exists. Rename the file and try again."
        }), 409

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    saved_name = f"{uuid.uuid4().hex}_{original_name}"
    file_path = os.path.join(upload_folder, saved_name)

    try:
        file.save(file_path)

        document = Document(
            organization_id=organization_id,
            uploaded_by=uploaded_by,
            name=original_name,
            file_path=file_path,
            mime_type=file.mimetype or "application/octet-stream"
        )

        db.session.add(document)
        db.session.commit()

    except Exception:
        db.session.rollback()

        if os.path.exists(file_path):
            os.remove(file_path)

        raise

    return jsonify({
    "id": document.id,
    "name": document.name,
    "organization_id": document.organization_id,
    "uploaded_by": document.uploaded_by,
    "mime_type": document.mime_type,
    "uploaded_at": document.uploaded_at.isoformat(),
    "message": "File uploaded successfully"
    }), 201

@document_bp.route("/", methods=["GET"])
@jwt_required()
def get_documents():
    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role == "superadmin":
        documents = Document.query.all()
    else:
        documents = Document.query.filter_by(
            organization_id=current_user.organization_id
        ).all()

    return jsonify([
        {
            "id": doc.id,
            "organization_id": doc.organization_id,
            "uploaded_by": doc.uploaded_by,
            "name": doc.name,
            "mime_type": doc.mime_type,
            "uploaded_at": doc.uploaded_at.isoformat()
        }
        for doc in documents
    ]), 200

@document_bp.route("/<int:document_id>", methods=["GET"])
@jwt_required()
def get_document(document_id):
    document = Document.query.get(document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role != "superadmin":
        if current_user.organization_id != document.organization_id:
            return jsonify({"error": "Access denied"}), 403

    return jsonify({
        "id": document.id,
        "organization_id": document.organization_id,
        "uploaded_by": document.uploaded_by,
        "name": document.name,
        "mime_type": document.mime_type,
        "uploaded_at": document.uploaded_at.isoformat()
    }), 200

@document_bp.route("/search", methods=["GET"])
@jwt_required()
def search_documents():
    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    name = request.args.get("name", "").strip()

    if not name:
        return jsonify({"error": "Please provide a filename to search"}), 400

    query = Document.query.filter(
        Document.name.ilike(f"%{name}%")
    )

    if current_user.role != "superadmin":
        query = query.filter_by(
            organization_id=current_user.organization_id
        )

    documents = query.all()

    return jsonify([
        {
            "id": doc.id,
            "organization_id": doc.organization_id,
            "uploaded_by": doc.uploaded_by,
            "name": doc.name,
            "mime_type": doc.mime_type,
            "uploaded_at": doc.uploaded_at.isoformat()
        }
        for doc in documents
    ]), 200

@document_bp.route("/<int:document_id>", methods=["DELETE"])
@jwt_required()
def delete_document(document_id):
    document = Document.query.get(document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role == "superadmin":
        pass
    elif current_user.role == "admin":
        if current_user.organization_id != document.organization_id:
            return jsonify({"error": "Access denied"}), 403
    elif current_user.role == "member":
        if current_user.organization_id != document.organization_id:
            return jsonify({"error": "Access denied"}), 403

        permission = Permission.query.filter_by(
            user_id=current_user.id,
            document_id=document.id
        ).first()

        if not permission or not permission.can_delete:
            return jsonify({
                "error": "You do not have permission to delete this document"
            }), 403
    else:
        return jsonify({"error": "Access denied"}), 403

    file_path = document.file_path

    permissions = Permission.query.filter_by(
        document_id=document.id
    ).all()

    Permission.query.filter_by(
        document_id=document.id
    ).delete(synchronize_session=False)

    db.session.flush()

    db.session.delete(document)
    db.session.commit()

    if os.path.exists(file_path):
        os.remove(file_path)

    return jsonify({
        "message": "Document deleted successfully"
    }), 200

@document_bp.route("/<int:document_id>/download", methods=["GET"])
@jwt_required()
def download_document(document_id):
    document = Document.query.get(document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role != "superadmin":
        if current_user.organization_id != document.organization_id:
            return jsonify({"error": "Access denied"}), 403

    if current_user.role == "member":
        permission = Permission.query.filter_by(
            user_id=current_user.id,
            document_id=document.id
        ).first()

        if not permission or not permission.can_download:
            return jsonify({
                "error": "You do not have permission to download this document"
            }), 403

    if not os.path.exists(document.file_path):
        return jsonify({"error": "Document file not found"}), 404

    return send_file(
        document.file_path,
        as_attachment=True,
        download_name=document.name,
        mimetype=document.mime_type
    )

@document_bp.route("/<int:document_id>/replace", methods=["PUT"])
@jwt_required()
def replace_document(document_id):
    document = Document.query.get(document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role == "superadmin":
        pass
    elif current_user.role == "admin":
        if current_user.organization_id != document.organization_id:
            return jsonify({"error": "Access denied"}), 403
    elif current_user.role == "member":
        if current_user.organization_id != document.organization_id:
            return jsonify({"error": "Access denied"}), 403

        permission = Permission.query.filter_by(
            user_id=current_user.id,
            document_id=document.id
        ).first()

        if not permission or not permission.can_edit:
            return jsonify({
                "error": "You do not have permission to edit this document"
            }), 403
    else:
        return jsonify({"error": "Access denied"}), 403

    file = request.files.get("file")

    if not file or not file.filename:
        return jsonify({"error": "A replacement file is required"}), 400

    original_name = secure_filename(file.filename)

    if "." not in original_name:
        return jsonify({"error": "Invalid filename"}), 400

    extension = original_name.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "File type not allowed"}), 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    saved_name = f"{uuid.uuid4().hex}_{original_name}"
    new_file_path = os.path.join(upload_folder, saved_name)

    try:
        file.save(new_file_path)

        old_file_path = document.file_path

        document.name = original_name
        document.file_path = new_file_path
        document.mime_type = file.mimetype or "application/octet-stream"

        db.session.commit()

        if os.path.exists(old_file_path):
            os.remove(old_file_path)

    except Exception:
        db.session.rollback()

        if os.path.exists(new_file_path):
            os.remove(new_file_path)

        raise

    return jsonify({
        "message": "Document replaced successfully",
        "id": document.id,
        "name": document.name,
        "mime_type": document.mime_type
    }), 200

@document_bp.route("/<int:document_id>/view", methods=["GET"])
@jwt_required()
def view_document(document_id):
    document = Document.query.get(document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    current_user = get_current_user()

    if not current_user:
        return jsonify({"error": "User not found"}), 404

    if current_user.role != "superadmin":
        if current_user.organization_id != document.organization_id:
            return jsonify({"error": "Access denied"}), 403

    if current_user.role == "member":
        permission = Permission.query.filter_by(
            user_id=current_user.id,
            document_id=document.id
        ).first()

        if not permission or not permission.can_view:
            return jsonify({
                "error": "You do not have permission to view this document"
            }), 403

    if not os.path.exists(document.file_path):
        return jsonify({"error": "Document file not found"}), 404

    return send_file(
        document.file_path,
        as_attachment=False,
        mimetype=document.mime_type
    )