from fastapi import FastAPI
from apps.users.views import router as user_router
app = FastAPI()

app.include_router(user_router, prefix="/users", tags=['User'])
