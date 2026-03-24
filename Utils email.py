import threading
import yagmail
from config import EMAIL_EMISOR, EMAIL_PASSWORD


def enviar_correo_base(destinatario, asunto, cuerpo):
    try:
        yag = yagmail.SMTP(EMAIL_EMISOR, EMAIL_PASSWORD)
        yag.send(to=destinatario, subject=asunto, contents=cuerpo)
    except Exception as e:
        print(f"Aviso - No se pudo enviar el correo: {e}")


def disparar_correo_async(destinatario, asunto, cuerpo):
    if destinatario:
        threading.Thread(
            target=enviar_correo_base,
            args=(destinatario, asunto, cuerpo)
        ).start()
