import os
import json
import smtplib
import feedparser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- Config ---
EMAIL_REMITENTE  = os.environ.get("EMAIL_REMITENTE", "")
EMAIL_CONTRASENA = os.environ.get("EMAIL_CONTRASENA", "")
EMAIL_DESTINO    = os.environ.get("EMAIL_DESTINO", "")

SEEN_JOBS_FILE = "seen_jobs.json"

# RSS feeds de Indeed para Louisville KY
# Puedes agregar mas busquedas cambiando el parametro q=
RSS_FEEDS = [
    "https://www.indeed.com/rss?q=&l=Louisville%2C+KY&sort=date",
    "https://www.indeed.com/rss?q=warehouse&l=Louisville%2C+KY&sort=date",
    "https://www.indeed.com/rss?q=restaurant&l=Louisville%2C+KY&sort=date",
    "https://www.indeed.com/rss?q=cleaning&l=Louisville%2C+KY&sort=date",
    "https://www.indeed.com/rss?q=construction&l=Louisville%2C+KY&sort=date",
]


def cargar_vistos():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def guardar_vistos(vistos):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(vistos), f)


def obtener_empleos():
    empleos = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                empleos.append({
                    "id":      entry.get("id", entry.get("link", "")),
                    "titulo":  entry.get("title", "Sin título"),
                    "empresa": entry.get("author", "Empresa no especificada"),
                    "link":    entry.get("link", ""),
                    "fecha":   entry.get("published", ""),
                })
        except Exception as e:
            print(f"Error al leer RSS {url}: {e}")
    return empleos


def enviar_email(nuevos):
    if not EMAIL_REMITENTE or not EMAIL_CONTRASENA or not EMAIL_DESTINO:
        print("ERROR: Faltan variables de entorno EMAIL_REMITENTE, EMAIL_CONTRASENA, EMAIL_DESTINO")
        return

    cuerpo_html = """
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
    <h2 style="color:#2563eb">🆕 Empleos Nuevos en Louisville, KY</h2>
    <p style="color:#6b7280">Se encontraron <strong>{count}</strong> empleos nuevos</p>
    """.format(count=len(nuevos))

    for job in nuevos:
        cuerpo_html += """
        <div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin:12px 0">
            <h3 style="margin:0 0 4px;color:#111827">{titulo}</h3>
            <p style="margin:0 0 8px;color:#6b7280;font-size:14px">🏢 {empresa}</p>
            <a href="{link}" style="background:#2563eb;color:white;padding:8px 16px;
               border-radius:4px;text-decoration:none;font-size:14px">Ver empleo →</a>
        </div>
        """.format(**job)

    cuerpo_html += """
    <p style="color:#9ca3af;font-size:12px;margin-top:24px">
        Alerta automática — Job Alert Louisville KY<br>
        {fecha}
    </p></body></html>
    """.format(fecha=datetime.now().strftime("%d/%m/%Y %H:%M"))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🆕 {len(nuevos)} empleos nuevos en Louisville, KY"
    msg["From"]    = EMAIL_REMITENTE
    msg["To"]      = EMAIL_DESTINO
    msg.attach(MIMEText(cuerpo_html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_REMITENTE, EMAIL_CONTRASENA)
            server.sendmail(EMAIL_REMITENTE, EMAIL_DESTINO, msg.as_string())
        print(f"Email enviado con {len(nuevos)} empleos nuevos")
    except Exception as e:
        print(f"Error al enviar email: {e}")


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Revisando empleos en Louisville, KY...")

    vistos     = cargar_vistos()
    empleos    = obtener_empleos()
    nuevos     = [j for j in empleos if j["id"] not in vistos]

    print(f"Total empleos encontrados: {len(empleos)} | Nuevos: {len(nuevos)}")

    if nuevos:
        enviar_email(nuevos)
        for j in nuevos:
            vistos.add(j["id"])
        guardar_vistos(vistos)
    else:
        print("No hay empleos nuevos.")


if __name__ == "__main__":
    main()
