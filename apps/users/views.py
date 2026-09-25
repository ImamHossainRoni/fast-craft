from fastapi import Depends, status
from apps.users.schemas import UserCreationResponseSchema, UserCreationSchema, UserResponseSchema
from apps.users.services import UserReadService, UserWriteService
from core.response import Response
from core.views import BaseView


class UserListView(BaseView):
    async def get(self, service: UserReadService = Depends()):
        users = await service.find_all()
        response_data = self.serialize(users, UserResponseSchema)
        return Response(response_data, status=status.HTTP_200_OK, msg="Users fetched successfully.")


class UserRegisterView(BaseView):
    async def register(self, user_data: UserCreationSchema, service: UserWriteService = Depends()):
        if await service.does_exist({"username": user_data.username}):
            return Response(status=status.HTTP_409_CONFLICT, msg="Username is already taken.")

        if await service.does_exist({"email": user_data.email}):
            return Response(status=status.HTTP_409_CONFLICT, msg="Email is already registered.")

        user = await service.register(user_data)
        response_data = self.serialize(user, UserCreationResponseSchema)
        return Response(response_data, status=status.HTTP_201_CREATED, msg="User registered successfully.")
