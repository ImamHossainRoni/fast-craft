from fastapi import APIRouter
from apps.users.views import UserListView, UserRegisterView
from core.enums import HTTP

router = APIRouter()

router.add_api_route("/", UserListView.as_view(), methods=[HTTP.GET], operation_id="list_users")
router.add_api_route("/", UserRegisterView.as_view(), methods=[HTTP.POST])
