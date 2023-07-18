from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from auth.auth import JWTBearer
from db.database import get_async_session
from user.schemas import UserSchema, UserCreateRequest, UserUpdateRequest, UserNewData
from user.models import UserModel
from utils.hashing import Hasher

router = APIRouter(prefix='/user')


@router.get("/", response_model=List[UserSchema], dependencies=[Depends(JWTBearer())])
async def get_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_session)):
    users = await UserModel.get_all(db, skip, limit)

    return users


@router.get("/{user_id}", response_model=UserSchema, dependencies=[Depends(JWTBearer())])
async def get_user_by_id(user_id: int, db: AsyncSession = Depends(get_async_session)):
    users = await UserModel.get_by_id(db, user_id)

    return users


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(request: UserCreateRequest, db: AsyncSession = Depends(get_async_session)):
    new_user = UserModel(
        email=request.email,
        username=request.username,
        hashed_password=Hasher.get_password_hash(request.password)
    )

    user = await new_user.create(db)

    return user


@router.put("/{user_id}", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def update_user(
        user_id: int,
        data: UserUpdateRequest,
        token_data: list = Depends(JWTBearer()),
        db: AsyncSession = Depends(get_async_session)
):
    user = await UserModel.get_by_fields(db, email=token_data['email'])

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Incorrect data in token')

    if not user.can_edit(user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='This user cannot change the data')

    user_update = await UserModel.update(db, user_id, UserNewData(data))

    return user_update


@router.delete("/{user_id}")
async def delete_user(
        user_id: int,
        token_data: list = Depends(JWTBearer()),
        db: AsyncSession = Depends(get_async_session)
):
    user = await UserModel.get_by_fields(db, email=token_data['email'])

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Incorrect data in token')

    if not user.can_delete(user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='This user cannot delete')

    return await UserModel.delete(db, user_id)