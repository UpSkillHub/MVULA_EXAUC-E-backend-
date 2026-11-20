"""
Swagger 2.0 specification for the Document Management System API.
This file documents the API without adding docstrings to individual routes.
"""

def response(description):
    return {"description": description}


def operation(summary, operation_id, *, parameters=None, protected=True,
              consumes=None, success="Successful response", extra_responses=None,
              tags=None, produces=None):
    result = {
        "summary": summary,
        "operationId": operation_id,
        "tags": tags or [],
        "produces": produces or ["application/json"],
        "responses": {"200": response(success)}
    }
    if parameters:
        result["parameters"] = parameters
    if protected:
        result["security"] = [{"Bearer": []}]
    if consumes:
        result["consumes"] = consumes
    if extra_responses:
        result["responses"].update({
            str(code): (
                definition if isinstance(definition, dict)
                else response(definition)
            )
            for code, definition in extra_responses.items()
        })
    return result

def path_parameter(name, description):
    return {
        "name": name, "in": "path", "required": True,
        "type": "integer", "format": "int32", "description": description
    }

def body_parameter(schema_name, description="Request body"):
    return {
        "name": "body", "in": "body", "required": True,
        "description": description,
        "schema": {"$ref": "#/definitions/" + schema_name}
    }

def form_parameter(name, description, required=True):
    return {
        "name": name, "in": "formData", "required": required,
        "type": "file" if name == "file" else "integer" if name == "organization_id" else "string",
        "description": description
    }

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "Document Management System API",
        "description": (
            "API for managing organizations, users, documents, and document "
            "permissions. Protected endpoints require a JWT access token. "
            "In Swagger's Authorize dialog, enter: Bearer <access_token>."
        ),
        "version": "1.0.0"
    },
    "basePath": "/",
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter: Bearer followed by your JWT access token."
        }
    },
    "definitions": {
        "LoginRequest": {
            "type": "object", "required": ["email", "password"],
            "properties": {
                "email": {"type": "string", "format": "email"},
                "password": {"type": "string", "format": "password"}
            }
        },
        "OrganizationCreate": {
            "type": "object", "required": ["name", "email"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"}
            }
        },
        "OrganizationUpdate": {
            "type": "object", "required": ["name", "email"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"}
            }
        },
        "UserRegistration": {
            "type": "object", "required": ["organization_id", "name", "email", "password"],
            "properties": {
                "organization_id": {"type": "integer"},
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "password": {"type": "string", "format": "password"}
            }
        },
        "UserUpdate": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"}
            }
        },
        "RoleUpdate": {
            "type": "object", "required": ["role"],
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["member", "admin", "superadmin"]
                }
            }
        },
        "PermissionCreate": {
            "type": "object", "required": ["user_id", "document_id"],
            "properties": {
                "user_id": {"type": "integer"},
                "document_id": {"type": "integer"},
                "can_view": {"type": "boolean", "default": False},
                "can_download": {"type": "boolean", "default": False},
                "can_edit": {"type": "boolean", "default": False},
                "can_delete": {"type": "boolean", "default": False}
            }
        },
        "PermissionUpdate": {
            "type": "object",
            "properties": {
                "can_view": {"type": "boolean"},
                "can_download": {"type": "boolean"},
                "can_edit": {"type": "boolean"},
                "can_delete": {"type": "boolean"}
            }
        },
        "Error": {
            "type": "object",
            "properties": {"error": {"type": "string"}}
        }
    },
    "paths": {}
}

P = SWAGGER_TEMPLATE["paths"]

# Authentication (1 endpoint)
P["/auth/login"] = {
    "post": operation(
        "Log in and receive a JWT access token", "login",
        parameters=[body_parameter("LoginRequest")], protected=False,
        success="Login successful; returns access_token and user details.",
        extra_responses={400: "Missing JSON data, email, or password.",
                         401: "Invalid email or password."},
        tags=["Authentication"]
    )
}

# Organizations (5 endpoints)
P["/organizations/"] = {
    "post": operation(
        "Create an organization (superadmin only)", "create_organization",
        parameters=[body_parameter("OrganizationCreate")],
        success="Organization created.",
        extra_responses={400: "Missing JSON data or required fields.",
                         403: "Superadmin access required.",
                         409: "Organization email already exists."},
        tags=["Organizations"]
    ),
    "get": operation(
        "List organizations", "list_organizations",
        success="Returns all organizations for a superadmin, or the current user's organization.",
        extra_responses={404: "Current user not found."},
        tags=["Organizations"]
    )
}
P["/organizations/{org_id}"] = {
    "get": operation(
        "Get an organization", "get_organization",
        parameters=[path_parameter("org_id", "Organization ID")],
        success="Organization details.",
        extra_responses={403: "Access denied.", 404: "User or organization not found."},
        tags=["Organizations"]
    ),
    "put": operation(
        "Update an organization (admin or superadmin)", "update_organization",
        parameters=[path_parameter("org_id", "Organization ID"),
                    body_parameter("OrganizationUpdate")],
        success="Updated organization details.",
        extra_responses={400: "Missing JSON data or required fields.",
                         403: "Role or organization access denied.",
                         404: "User or organization not found."},
        tags=["Organizations"]
    ),
    "delete": operation(
        "Delete an organization (admin or superadmin)", "delete_organization",
        parameters=[path_parameter("org_id", "Organization ID")],
        success="Organization deleted.",
        extra_responses={403: "Role or organization access denied.",
                         404: "User or organization not found."},
        tags=["Organizations"]
    )
}

# Users (6 endpoints)
P["/users/register"] = {
    "post": operation(
        "Register a member in an organization", "register_user",
        parameters=[body_parameter("UserRegistration")], protected=False,
        success="User created with the member role.",
        extra_responses={400: "Required fields or organization ID missing.",
                         404: "Organization not found.",
                         409: "A user with this email already exists."},
        tags=["Users"]
    )
}
P["/users/"] = {
    "get": operation(
        "List users visible to the current user", "list_users",
        success="Returns users according to the current user's role.",
        extra_responses={404: "Current user not found."},
        tags=["Users"]
    )
}
P["/users/{user_id}"] = {
    "get": operation(
        "Get a user", "get_user",
        parameters=[path_parameter("user_id", "User ID")],
        success="User details.",
        extra_responses={403: "Access denied.", 404: "User not found."},
        tags=["Users"]
    ),
    "put": operation(
        "Update a user's name or email", "update_user",
        parameters=[path_parameter("user_id", "User ID"),
                    body_parameter("UserUpdate")],
        success="Updated user details.",
        extra_responses={400: "Request body is required.",
                         403: "Access denied.", 404: "User not found."},
        tags=["Users"]
    ),
    "delete": operation(
        "Delete a user", "delete_user",
        parameters=[path_parameter("user_id", "User ID")],
        success="User deleted.",
        extra_responses={403: "Access denied or admin is not allowed to delete this role.",
                         404: "User not found."},
        tags=["Users"]
    )
}
P["/users/{user_id}/role"] = {
    "put": operation(
        "Change a user's role", "change_user_role",
        parameters=[path_parameter("user_id", "User ID"),
                    body_parameter("RoleUpdate")],
        success="Updated user details and role.",
        extra_responses={400: "Role missing/invalid or target-user role constraints not met.",
                         403: "Access denied or role change not allowed.",
                         404: "Current user or target user not found."},
        tags=["Users"]
    )
}

# Documents (8 endpoints)
P["/documents/upload"] = {
    "post": operation(
        "Upload a document", "upload_document",
        parameters=[
            form_parameter("file", "Document file to upload."),
            form_parameter("organization_id", "ID of the organization.")
        ],
        consumes=["multipart/form-data"],
        success="Document uploaded; returns document metadata.",
        extra_responses={400: "Missing file/organization ID or invalid file name/type.",
                         403: "Organization access denied.",
                         404: "Current user or organization not found.",
                         409: "A document with this filename already exists in the organization."},
        tags=["Documents"]
    )
}
P["/documents/"] = {
    "get": operation(
        "List documents accessible to the current user", "list_documents",
        success="Returns document metadata.",
        extra_responses={404: "Current user not found."},
        tags=["Documents"]
    )
}
P["/documents/search"] = {
    "get": operation(
        "Search documents by filename", "search_documents",
        parameters=[{
            "name": "name", "in": "query", "required": True,
            "type": "string", "description": "Full or partial filename to search for."
        }],
        success="Returns matching document metadata.",
        extra_responses={400: "Search name is missing.", 404: "Current user not found."},
        tags=["Documents"]
    )
}
P["/documents/{document_id}"] = {
    "get": operation(
        "Get document metadata", "get_document",
        parameters=[path_parameter("document_id", "Document ID")],
        success="Document metadata.",
        extra_responses={403: "Access denied.", 404: "Document or current user not found."},
        tags=["Documents"]
    ),
    "delete": operation(
        "Delete a document", "delete_document",
        parameters=[path_parameter("document_id", "Document ID")],
        success="Document deleted.",
        extra_responses={403: "Access denied or can_delete permission is missing.",
                         404: "Document or current user not found."},
        tags=["Documents"]
    )
}
P["/documents/{document_id}/download"] = {
    "get": operation(
        "Download a document", "download_document",
        parameters=[path_parameter("document_id", "Document ID")],
        success="Returns the document as a file attachment.",
        extra_responses={403: "Access denied or can_download permission is missing.",
                         404: "Document, current user, or stored file not found."},
        tags=["Documents"]
    )
}
P["/documents/{document_id}/replace"] = {
    "put": operation(
        "Replace a document's file", "replace_document",
        parameters=[path_parameter("document_id", "Document ID"),
                    form_parameter("file", "Replacement document file.")],
        consumes=["multipart/form-data"],
        success="Document file replaced; returns updated metadata.",
        extra_responses={400: "Replacement file missing or invalid filename/type.",
                         403: "Access denied or can_edit permission is missing.",
                         404: "Document or current user not found."},
        tags=["Documents"]
    )
}
P["/documents/{document_id}/view"] = {
    "get": operation(
        "View a document in the browser", "view_document",
        parameters=[
            path_parameter("document_id", "Document ID")
        ],
        success="Document file returned successfully.",
        produces=[
            "application/pdf",
            "image/png",
            "image/jpeg",
            "application/octet-stream"
        ],
        extra_responses={
            200: {
                "description": "Document file returned successfully.",
                "schema": {
                    "type": "file"
                }
            },
            403: "Access denied or can_view permission is missing.",
            404: "Document, current user, or stored file not found."
        },
        tags=["Documents"]
    )
}
# Permissions (5 endpoints)
P["/permissions/"] = {
    "post": operation(
        "Assign document permissions to a user", "assign_permission",
        parameters=[body_parameter("PermissionCreate")],
        success="Permission created.",
        extra_responses={400: "Missing JSON data or permissions cannot be assigned to a superadmin.",
                         403: "Access denied or user/document is outside the admin's organization.",
                         404: "Current user, target user, or document not found.",
                         409: "Permission already exists."},
        tags=["Permissions"]
    ),
    "get": operation(
        "List permissions", "list_permissions",
        success="Returns permissions visible to the current admin or superadmin.",
        extra_responses={403: "Access denied.", 404: "Current user not found."},
        tags=["Permissions"]
    )
}
P["/permissions/{permission_id}"] = {
    "get": operation(
        "Get a permission", "get_permission",
        parameters=[path_parameter("permission_id", "Permission ID")],
        success="Permission details.",
        extra_responses={403: "Access denied.", 404: "User, permission, or document not found."},
        tags=["Permissions"]
    ),
    "put": operation(
        "Update document permissions", "update_permission",
        parameters=[path_parameter("permission_id", "Permission ID"),
                    body_parameter("PermissionUpdate")],
        success="Updated permission details.",
        extra_responses={400: "JSON data is required.",
                         403: "Access denied.", 404: "User, permission, or document not found."},
        tags=["Permissions"]
    ),
    "delete": operation(
        "Delete a permission", "delete_permission",
        parameters=[path_parameter("permission_id", "Permission ID")],
        success="Permission deleted.",
        extra_responses={403: "Access denied.", 404: "User, permission, or document not found."},
        tags=["Permissions"]
    )
}
