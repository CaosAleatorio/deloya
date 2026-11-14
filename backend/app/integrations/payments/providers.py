from abc import ABC, abstractmethod

from fastapi import HTTPException

from app.core.config import get_settings


class PaymentProvider(ABC):
    @abstractmethod
    def ensure_available(self) -> None:
        """Fail closed until an authorised, documented adapter is available."""

    def verify_callback(self, payload: bytes, headers: dict) -> bool:
        return False


class DemoPaymentProvider(PaymentProvider):
    def ensure_available(self):
        if get_settings().payment_mode != "demo":
            raise HTTPException(503, "O modo de demonstração não está activo")


class MPesaProvider(PaymentProvider):
    def ensure_available(self):
        raise HTTPException(503, "M-Pesa real desactivado: requer acesso autorizado e validação da documentação oficial")


class EMolaProvider(PaymentProvider):
    def ensure_available(self):
        raise HTTPException(503, "e-Mola real desactivado: requer documentação comercial e credenciais autorizadas")
