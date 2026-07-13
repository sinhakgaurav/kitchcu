from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://ckac:ckac_dev@localhost:5432/ckac"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7
    cors_origins: str = "http://localhost:3001,http://localhost:5173"
    identity_service_url: str = "http://localhost:8001"
    catalog_service_url: str = "http://localhost:8002"
    order_service_url: str = "http://localhost:8003"
    billing_service_url: str = "http://localhost:8004"
    notification_service_url: str = "http://localhost:8005"
    marketing_service_url: str = "http://localhost:8006"
    ratings_service_url: str = "http://localhost:8007"
    growth_service_url: str = "http://localhost:8008"
    delivery_service_url: str = "http://localhost:8009"
    learning_service_url: str = "http://localhost:8010"
    internal_api_key: str = "dev-internal-key-change-in-production"
    whatsapp_verify_token: str = "ckac-dev-verify"
    admin_email: str = "admin@kitchcu.dev"
    admin_password: str = "admin123456"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "ckac"
    minio_secret_key: str = "ckac_minio_dev"
    minio_bucket: str = "ckac-media"
    minio_public_url: str = "http://localhost:9000"
    minio_secure: bool = False
    media_storage_backend: str = "minio"  # minio | local (tests)
    media_local_dir: str = "/tmp/ckac-media"

    oauth_google_client_id: str = ""
    oauth_google_client_secret: str = ""
    oauth_facebook_client_id: str = ""
    oauth_facebook_client_secret: str = ""
    oauth_instagram_client_id: str = ""
    oauth_instagram_client_secret: str = ""
    oauth_twitter_client_id: str = ""
    oauth_twitter_client_secret: str = ""
    customer_oauth_redirect_base: str = "http://localhost:13001"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
