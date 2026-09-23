#! python
# -*- coding: utf-8 -*-

"""
Module: management/commands/startapp.py

Description: Scaffolds a new app inside the 'apps' directory.

Usage:
    python manage.py startapp <app_name>
"""
import argparse
import os
import sys

from core.management.commands.base import BaseCommand

APPS_DIR = "apps"


def _files(app_name: str) -> dict:
    model_name = app_name.capitalize()

    return {
        "__init__.py": "",
        "models.py": (
            "from sqlalchemy import Column, String\n"
            "\n"
            "from core.models import BaseModel\n"
            "\n\n"
            f"class {model_name}(BaseModel):\n"
            f"    __tablename__ = \"{app_name}\"\n"
            "\n"
            "    name = Column(String)  # placeholder field - add your real columns here\n"
        ),
        "schemas.py": (
            "from pydantic import BaseModel\n"
            "\n\n"
            f"class {model_name}BaseSchema(BaseModel):\n"
            "    pass\n"
            "\n\n"
            f"class {model_name}Schema({model_name}BaseSchema):\n"
            "    \"\"\"Input schema, e.g. for create/update request bodies.\"\"\"\n"
            "\n\n"
            f"class {model_name}ResponseSchema({model_name}BaseSchema):\n"
            "    \"\"\"Output schema, e.g. for API responses (set model_config ="
            " ConfigDict(from_attributes=True) if built from an ORM object).\"\"\"\n"
        ),
        "dao.py": (
            "from typing import Type\n"
            "\n"
            "from core.dao import Dao\n"
            f"from apps.{app_name}.models import {model_name}\n"
            "\n\n"
            f"class {model_name}Dao(Dao):\n"
            "    @property\n"
            f"    def model_cls(self) -> Type[{model_name}]:\n"
            f"        return {model_name}\n"
        ),
        "services.py": (
            "from typing import Type\n"
            "\n"
            "from core.dao import Dao\n"
            "from core.service import ReadService, WriteService\n"
            f"from apps.{app_name}.dao import {model_name}Dao\n"
            "\n\n"
            f"class {model_name}ReadService(ReadService):\n"
            "    @property\n"
            "    def dao_cls(self) -> Type[Dao]:\n"
            f"        return {model_name}Dao\n"
            "\n\n"
            f"class {model_name}WriteService(WriteService):\n"
            "    @property\n"
            "    def dao_cls(self) -> Type[Dao]:\n"
            f"        return {model_name}Dao\n"
        ),
        "views.py": (
            "from fastapi import Request, status\n"
            "\n"
            f"from apps.{app_name}.services import {model_name}ReadService, {model_name}WriteService\n"
            "from core.response import Response\n"
            "from core.views import APIView\n"
            "\n\n"
            f"class {model_name}ListAPIView(APIView):\n"
            f"    # Pass the output schema directly to self.serialize(obj, {model_name}ResponseSchema)\n"
            "    # at each call site - DRF-style (e.g. TokenSerializer(tokens).data), so a method whose\n"
            "    # output shape differs from another method's just names its own schema where it's used.\n"
            "    #\n"
            "    # as_view() (see urls.py) dispatches by request.method at request time, so FastAPI never\n"
            "    # inspects get()'s/post()'s own signature - Depends() doesn't work here. Build services via\n"
            "    # self.get_service(...) instead, and read + validate a body yourself, e.g. in post():\n"
            f"    #     data = {model_name}Schema.model_validate(await request.json())\n"
            "\n"
            f"    async def get(self, request: Request):\n"
            f"        service = await self.get_service({model_name}ReadService)\n"
            "        items = await service.find_all()\n"
            f"        return Response(items, status=status.HTTP_200_OK, msg=\"{model_name} fetched successfully.\")\n"
            "\n"
            f"    async def post(self, request: Request):\n"
            f"        service = await self.get_service({model_name}WriteService)\n"
            "        # data = await service.create(...)\n"
            f"        return Response(status=status.HTTP_201_CREATED, msg=\"{model_name} created successfully.\")\n"
        ),
        "urls.py": (
            "from fastapi import APIRouter\n"
            "\n"
            f"from apps.{app_name}.views import {model_name}ListAPIView\n"
            "from core.enums import HTTP\n"
            "\n"
            "router = APIRouter()\n"
            "\n"
            f"router.add_api_route(\"/\", {model_name}ListAPIView.as_view(), methods=[HTTP.GET, HTTP.POST])\n"
        ),
    }


class Command(BaseCommand):
    name = "startapp"
    help = "Create a new app inside the apps directory"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("app_name", type=str, help="Name of the new app")

    def handle(self, args: argparse.Namespace) -> None:
        app_name = args.app_name
        app_dir = os.path.join(APPS_DIR, app_name)

        if os.path.exists(app_dir):
            sys.exit(f'❌ App "{app_name}" already exists at "{app_dir}".')

        os.makedirs(app_dir)

        for filename, content in _files(app_name).items():
            file_path = os.path.join(app_dir, filename)
            with open(file_path, "w") as f:
                f.write(content)

        print(f'➡️ Successfully created app "{app_name}" inside the "{APPS_DIR}" directory with the desired files. 👍')
        print(f'   Remember to include its router in urls.py, e.g.:')
        print(f'   from apps.{app_name}.urls import router as {app_name}_router')
        print(f'   router.include_router({app_name}_router, prefix="/{app_name}", tags=["{app_name.capitalize()}"], responses=NOT_FOUND_RESPONSE)')
