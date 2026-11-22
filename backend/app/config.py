from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Core ──────────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://nagaraai:nagaraai123@localhost:5432/nagaraai_db"
    SECRET_KEY: str = "dev-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ── IBM watsonx.ai ────────────────────────────────────────────────────────
    WATSONX_API_KEY: str = ""
    WATSONX_PROJECT_ID: str = ""
    WATSONX_URL: str = "https://us-south.ml.cloud.ibm.com"

    # ── Twilio (WhatsApp, SMS, MMS, Voice) ────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""          # E.164 e.g. +14155238886
    TWILIO_WHATSAPP_NUMBER: str = ""       # e.g. whatsapp:+14155238886
    TWILIO_VERIFY_SIGNATURE: bool = True   # set False only for local dev

    # ── Telegram Bot ──────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    # ── Email (SMTP) ──────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "nagaraai@example.com"
    SMTP_INTAKE_ADDRESS: str = ""          # inbound address polled for new reports

    # ── Social media webhooks (Meta / X / Instagram) ──────────────────────────
    META_APP_SECRET: str = ""              # Facebook + Instagram webhook verification
    META_VERIFY_TOKEN: str = "nagaraai-verify"
    META_PAGE_ACCESS_TOKEN: str = ""       # Facebook page token for outbound messages
    META_IG_ACCESS_TOKEN: str = ""         # Instagram graph token
    TWITTER_BEARER_TOKEN: str = ""
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_ACCESS_TOKEN: str = ""
    TWITTER_ACCESS_SECRET: str = ""
    TWITTER_WEBHOOK_ENV: str = "prod"

    # ── App base URL (used for webhook self-registration) ─────────────────────
    APP_BASE_URL: str = "https://nagaraai.example.com"

settings = Settings()
