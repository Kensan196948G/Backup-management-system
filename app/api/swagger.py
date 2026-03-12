"""OpenAPI/Swagger ドキュメント設定モジュール"""
from flasgger import Swagger

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/api/v1/apispec.json",
            "rule_filter": lambda rule: rule.rule.startswith("/api/v1"),
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/v1/docs",
}

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "バックアップ管理システム API",
        "description": "Backup Management System REST API v1",
        "version": "1.0.0",
        "contact": {
            "name": "Backup Management System",
        },
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        },
        "BearerAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
        },
    },
    "consumes": ["application/json"],
    "produces": ["application/json"],
}


def init_swagger(app):
    """Swagger UI を Flask アプリに初期化する"""
    swagger = Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)
    return swagger
