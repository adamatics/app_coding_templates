import importlib
import pkgutil

from fastapi import FastAPI

import app.api.routes as routes_pkg


def include_all_routers(app: FastAPI, prefix: str = "") -> None:
    for module_info in pkgutil.iter_modules(routes_pkg.__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"app.api.routes.{module_info.name}")
        router = getattr(module, "router", None)
        if router is not None:
            app.include_router(router, prefix=prefix)
