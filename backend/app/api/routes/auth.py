"""Authentication and User Management routes (JWT + RBAC)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import (
    ROLE_ADMIN,
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)
from backend.app.governance.audit_service import record_audit_log
from backend.app.models.metadata import User
from backend.app.schemas.api import LoginRequest, UserCreateRequest, UserUpdateRequest

router = APIRouter(prefix="/api/auth", tags=["Authentication & RBAC"])


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user credentials and issue a signed JWT token."""
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        record_audit_log(
            db,
            actor=payload.username,
            actor_role="Unknown",
            action="LOGIN_FAILED",
            resource_type="auth",
            resource_id=payload.username,
            execution_status="FAILED",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled.")

    token = create_access_token(subject=user.username, role=user.role, user_id=user.id)
    record_audit_log(
        db,
        actor=user.username,
        actor_role=user.role,
        action="LOGIN_SUCCESS",
        resource_type="auth",
        resource_id=user.username,
    )
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Return currently authenticated user profile."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }


@router.get("/users")
def list_users(
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """List application users (Administrator only)."""
    users = db.query(User).order_by(User.id.asc()).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Create a new application user (Administrator only)."""
    if db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists.")
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="USER_CREATED",
        resource_type="user",
        resource_id=user.username,
        updated_value=f"role={user.role}",
    )
    db.commit()
    return {"id": user.id, "username": user.username, "role": user.role, "email": user.email}


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Update user role or active status (Administrator only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    prev = f"role={user.role}, is_active={user.is_active}"
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.full_name is not None:
        user.full_name = payload.full_name
    new_val = f"role={user.role}, is_active={user.is_active}"
    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="USER_UPDATED",
        resource_type="user",
        resource_id=user.username,
        previous_value=prev,
        updated_value=new_val,
    )
    db.commit()
    return {"id": user.id, "username": user.username, "role": user.role, "is_active": user.is_active}
