from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.auth import UserCreate, UserResponse, UserUpdate
from app.utils.security import get_password_hash
from app.api.deps import get_admin_user

router = APIRouter(prefix="/users", tags=["User Administration"])


@router.get("", response_model=List[UserResponse])
async def list_users(
    current_admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).order_by(User.created_at)
    res = await db.execute(stmt)
    return [UserResponse.model_validate(u) for u in res.scalars().all()]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    current_admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if username exists
    stmt = select(User).where(User.username == user_in.username)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check email
    stmt = select(User).where(User.email == user_in.email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name or "",
        role=user_in.role,
        is_active=True,
    )
    db.add(new_user)

    # Audit
    audit = AuditLog(
        user_id=current_admin.id,
        username=current_admin.username,
        action="USER_CREATE",
        resource_type="USER",
        resource_id=new_user.username,
        details={"role": new_user.role, "email": new_user.email},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(new_user)
    return UserResponse.model_validate(new_user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.email is not None:
        user.email = user_update.email
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.role is not None:
        user.role = user_update.role
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.password is not None:
        user.hashed_password = get_password_hash(user_update.password)

    audit = AuditLog(
        user_id=current_admin.id,
        username=current_admin.username,
        action="USER_UPDATE",
        resource_type="USER",
        resource_id=user.username,
        details={"updated_fields": list(user_update.model_dump(exclude_unset=True).keys())},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)
