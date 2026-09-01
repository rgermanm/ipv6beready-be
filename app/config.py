from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "IPv6BeReady API"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    secret_key: str = "change-me-in-production-ipv6beready"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    google_client_id: str = ""
    recaptcha_secret_key: str = ""
    # When True, skip Docker and simulate container startup (useful for local dev)
    mock_containers: bool = False
    lab_host: str = "localhost"
    docker_network: str = "ipv6beready-fe_lab-net"
    clab_remote_host: str = "66.97.37.101"
    clab_remote_port: int = 5412
    clab_remote_username: str = "root"
    clab_remote_password: str = ""
    mongodb_uri: str = (
        "mongodb://admin:I6brReady--k8mQ2nP91x@66.97.37.101:27019/?authSource=admin"
    )
    mongodb_db: str = "ipv6beready"
    # Optional SSH tunnel when the Mongo port is firewalled
    mongodb_ssh_tunnel: bool = False
    mongodb_tunnel_host: str = "127.0.0.1"
    mongodb_tunnel_port: int = 27019
    # Lifetime of a per-user containerlab instance
    lab_ttl_seconds: int = 1800


settings = Settings()
