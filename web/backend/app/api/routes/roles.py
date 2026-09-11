from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import client_ip, require_permission
from app.core.permissions import (
    ALL_PERMISSIONS,
    PERMISSION_DESCRIPTIONS,
    Permission,
)
from app.models.role import Role
from app.models.user import User
from app.schemas.common import Message
from app.schemas.role import (
    PermissionCatalog,
    PermissionOut,
    RoleCreate,
    RoleOut,
    RoleUpdate,
)
from app.services import audit_service

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/permissions", response_model=PermissionCatalog)
async def permission_catalog(
    _: User = Depends(require_permission(Permission.ROLE_READ)),
) -> PermissionCatalog:
    return PermissionCatalog(
        permissions=[
            PermissionOut(key=k, description=PERMISSION_DESCRIPTIONS.get(k, k))
            for k in ALL_PERMISSIONS
        ]
    )


@router.get("", response_model=list[RoleOut])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.ROLE_READ)),
) -> list[Role]:
    result = await db.execute(select(Role).order_by(Role.name))
    return list(result.scalars().all())


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    body: RoleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.ROLE_MANAGE)),
) -> Role:
    if await db.scalar(select(Role).where(Role.name == body.name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")
    invalid = set(body.permissions) - set(ALL_PERMISSIONS)
    if invalid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown permissions: {sorted(invalid)}")

    role = Role(name=body.name, description=body.description, is_system=False)
    role.set_permissions(body.permissions)
    db.add(role)
    await db.commit()
    await audit_service.record(
        db, action="role.create", actor=actor, resource_type="role", resource_id=role.id,
        ip_address=client_ip(request), detail=body.name,
    )
    return role


@router.patch("/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: int,
    body: RoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.ROLE_MANAGE)),
) -> Role:
    role = await db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if body.description is not None:
        role.description = body.description
    if body.permissions is not None:
        if role.is_system:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System role permissions are locked")
        invalid = set(body.permissions) - set(ALL_PERMISSIONS)
        if invalid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown permissions: {sorted(invalid)}")
        role.set_permissions(body.permissions)

    await db.commit()
    await audit_service.record(
        db, action="role.update", actor=actor, resource_type="role", resource_id=role.id,
        ip_address=client_ip(request),
    )
    return role


@router.delete("/{role_id}", response_model=Message)
async def delete_role(
    role_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.ROLE_MANAGE)),
) -> Message:
    role = await db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete a system role")
    assigned = await db.scalar(select(func.count(User.id)).where(User.role_id == role_id)) or 0
    if assigned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role still assigned to users")

    name = role.name
    await db.delete(role)
    await db.commit()
    await audit_service.record(
        db, action="role.delete", actor=actor, resource_type="role", resource_id=role_id,
        ip_address=client_ip(request), detail=name,
    )
    return Message(message="Role deleted")
