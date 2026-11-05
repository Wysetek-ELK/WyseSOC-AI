from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.auth import Token, LoginRequest, UserResponse
from app.utils.security import verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.username == login_data.username)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        # Audit failed login
        audit_fail = AuditLog(
            username=login_data.username,
            action="LOGIN_FAILED",
            resource_type="USER",
            resource_id=login_data.username,
            details={"reason": "Invalid credentials"},
            ip_address=request.client.host if request.client else None,
        )
        db.add(audit_fail)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact an administrator.",
        )

    # Generate token
    token_data = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
    }
    access_token = create_access_token(token_data)

    # Set secure HttpOnly cookie
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )

    # Audit successful login
    audit_success = AuditLog(
        user_id=user.id,
        username=user.username,
        action="LOGIN_SUCCESS",
        resource_type="USER",
        resource_id=user.id,
        details={"role": user.role},
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit_success)
    await db.commit()

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )

    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="LOGOUT",
        resource_type="USER",
        resource_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
