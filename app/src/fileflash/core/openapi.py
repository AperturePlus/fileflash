from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def configure_openapi(app: FastAPI) -> None:
    """Expose Swagger UI auth for raw JWT (Apifox-friendly) — similar role to Knife4j in Java."""

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=getattr(app, "version", "1.0.0"),
            routes=app.routes,
            description=(
                "FileFlash HTTP API。调试建议：浏览器打开 /docs ，"
                "先调用 POST /api/v1/auth/login，再在 Authorize 中粘贴 data.token（无需 Bearer）。"
            ),
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})
        schema["components"]["securitySchemes"].update(
            {
                "AccessToken": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Authorization",
                    "description": "登录响应 data.token，可直接粘贴整段 JWT（也支持 Bearer 前缀）",
                },
                "XAccessToken": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Access-Token",
                    "description": "可选：仅粘贴 token，不含 Bearer",
                },
            }
        )
        schema["security"] = [{"AccessToken": []}, {"XAccessToken": []}]
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
