from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType, MultipartSubtypeEnum

from ..core.settings import Settings


class EmailDeliveryConfigurationError(RuntimeError):
    pass


class EmailDeliveryError(RuntimeError):
    pass


@dataclass(slots=True)
class VerificationEmailPayload:
    email: str
    token: str
    expires_in_minutes: int


class VerificationEmailDeliveryService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send_verification_email(
        self,
        *,
        email: str,
        token: str,
        expires_in_minutes: int,
    ) -> None:
        payload = VerificationEmailPayload(
            email=email.strip(),
            token=token.strip(),
            expires_in_minutes=expires_in_minutes,
        )
        self._validate_payload(payload)
        config = self._build_connection_config()
        verification_link = self._build_verification_link(payload.token)
        message = MessageSchema(
            subject="Verify your FileFlash email",
            recipients=[payload.email],
            body=self._build_html_body(
                verification_link=verification_link,
                expires_in_minutes=payload.expires_in_minutes,
            ),
            alternative_body=self._build_text_body(
                verification_link=verification_link,
                expires_in_minutes=payload.expires_in_minutes,
            ),
            subtype=MessageType.html,
            multipart_subtype=MultipartSubtypeEnum.alternative,
        )
        try:
            await FastMail(config).send_message(message)
        except Exception as exc:  # noqa: BLE001
            raise EmailDeliveryError("Failed to send verification email") from exc

    def _build_connection_config(self) -> ConnectionConfig:
        issues = self.settings.mail_configuration_issues
        if issues:
            raise EmailDeliveryConfigurationError(f"Mail delivery is not configured: {', '.join(issues)}")

        return ConnectionConfig(
            MAIL_USERNAME=(self.settings.mail_username or "").strip(),
            MAIL_PASSWORD=(self.settings.mail_password or "").strip(),
            MAIL_FROM=(self.settings.mail_from or "").strip(),
            MAIL_PORT=self.settings.mail_port,
            MAIL_SERVER=(self.settings.mail_server or "").strip(),
            MAIL_STARTTLS=self.settings.mail_starttls,
            MAIL_SSL_TLS=self.settings.mail_ssl_tls,
            USE_CREDENTIALS=self.settings.mail_use_credentials,
            VALIDATE_CERTS=self.settings.mail_validate_certs,
        )

    def _build_verification_link(self, token: str) -> str:
        base = self.settings.normalized_email_verify_base_url
        encoded_token = quote(token, safe="")
        return f"{base}/verify-email?token={encoded_token}"

    @staticmethod
    def _build_text_body(*, verification_link: str, expires_in_minutes: int) -> str:
        return (
            "Welcome to FileFlash.\n\n"
            "Please verify your email by opening the following link:\n"
            f"{verification_link}\n\n"
            f"This link expires in {expires_in_minutes} minutes."
        )

    @staticmethod
    def _build_html_body(*, verification_link: str, expires_in_minutes: int) -> str:
        return (
            "<!doctype html>"
            "<html lang=\"en\">"
            "<head>"
            "<meta charset=\"utf-8\" />"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />"
            "<title>Verify your FileFlash email</title>"
            "</head>"
            "<body style=\"margin:0;padding:0;background:#0E0E10;font-family:'Segoe UI',Arial,sans-serif;color:#E8E6DF;\">"
            "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"padding:24px 12px;\">"
            "<tr><td align=\"center\">"
            "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
            "style=\"max-width:560px;background:#15151A;border:1px solid #2A2A30;border-radius:14px;overflow:hidden;\">"
            "<tr><td style=\"padding:28px 28px 20px;\">"
            "<div style=\"font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#8A8A8A;\">FileFlash</div>"
            "<h1 style=\"margin:10px 0 12px;font-size:26px;line-height:1.2;color:#E8E6DF;\">Verify your email</h1>"
            "<p style=\"margin:0 0 16px;font-size:15px;line-height:1.7;color:#B8B5AC;\">"
            "Confirm your account to unlock the complete FileFlash experience."
            "</p>"
            "<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" style=\"margin:0 0 16px;\">"
            "<tr><td style=\"border-radius:10px;background:#B6FF3D;\">"
            f"<a href=\"{verification_link}\" "
            "style=\"display:inline-block;padding:12px 18px;font-size:14px;font-weight:700;color:#0E0E10;text-decoration:none;\">"
            "Verify Email</a></td></tr></table>"
            f"<p style=\"margin:0 0 6px;font-size:13px;color:#8A8A8A;\">Link expires in {expires_in_minutes} minutes.</p>"
            "<p style=\"margin:0;font-size:13px;color:#8A8A8A;word-break:break-all;\">"
            "If the button does not work, open this URL in your browser:<br />"
            f"<a href=\"{verification_link}\" style=\"color:#B6FF3D;\">{verification_link}</a>"
            "</p>"
            "</td></tr></table>"
            "</td></tr></table>"
            "</body></html>"
        )

    @staticmethod
    def _validate_payload(payload: VerificationEmailPayload) -> None:
        if not payload.email:
            raise EmailDeliveryError("Verification email target is empty")
        if not payload.token:
            raise EmailDeliveryError("Verification token is empty")
        if payload.expires_in_minutes <= 0:
            raise EmailDeliveryError("Verification email expiry must be positive")
