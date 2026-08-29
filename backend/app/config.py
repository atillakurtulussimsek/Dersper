"""Uygulama ayarları. Değerler .env dosyasından okunur."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "mysql+pymysql://root@127.0.0.1:3306/dersper?charset=utf8mb4"

    secret_key: str = "degistir-beni"
    access_token_expire_minutes: int = 720
    encryption_key: str = "degistir-beni"

    # Herkese açık kurum kaydı. Kapalıyken yalnızca sistemde hiç kurum yokken
    # (ilk kurulum) kayıt yapılabilir.
    allow_registration: bool = True

    # Arayüz üretimde aynı kökenden sunulur, bu yüzden CORS'a gerek yoktur ve
    # varsayılan boştur. Yalnızca API'yi başka bir kökenden çağıracaksanız
    # (örneğin ayrı bir alan adındaki istemci) virgülle ayırıp doldurun.
    # Geliştirmede Vite /api'yi kendisi proxy'lediği için yine gerekmez.
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
