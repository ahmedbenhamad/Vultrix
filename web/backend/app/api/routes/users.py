from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import client_ip, require_permission
from app.core.permissions import Permission
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services import audit_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.USER_READ)),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[UserOut]:
    stmt = select(User)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(User.email).like(like) | func.lower(User.full_name).like(like))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.execute(
        stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    rows = result.scalars().all()
    return Page(items=[UserOut.model_validate(u) for u in rows], total=total, page=page, page_size=page_size)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.USER_CREATE)),
) -> User:
    if await db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    role = await db.get(Role, body.role_id) if body.role_id else None
    if body.role_id and role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role not found")

    user = User(
        email=body.email.lower(),
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        is_active=body.is_active,
        role=role,
    )
    db.add(user)
    await db.commit()
    await audit_service.record(
        db, action="user.create", actor=actor, resource_type="user", resource_id=user.id,
        ip_address=client_ip(request), detail=f"Created {user.email}",
    )
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.USER_READ)),
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.USER_UPDATE)),
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None:
        if user.id == actor.id and body.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot disable your own account")
        user.is_active = body.is_active
    if body.role_id is not None:
        role = await db.get(Role, body.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role not found")
        user.role = role
    if body.password:
        user.password_hash = hash_password(body.password)

    await db.commit()
    await audit_service.record(
        db, action="user.update", actor=actor, resource_type="user", resource_id=user.id,
        ip_address=client_ip(request),
    )
    return user


@router.delete("/{user_id}", response_model=Message)
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.USER_DELETE)),
) -> Message:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == actor.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")

    email = user.email
    await db.delete(user)
    await db.commit()
    await audit_service.record(
        db, action="user.delete", actor=actor, resource_type="user", resource_id=user_id,
        ip_address=client_ip(request), detail=f"Deleted {email}",
    )
    return Message(message="User deleted")
