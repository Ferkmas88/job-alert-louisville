import os
import json
import smtplib
import feedparser
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- Config ---
EMAIL_REMITENTE  = os.environ.get("EMAIL_REMITENTE", "")
EMAIL_CONTRASENA = os.environ.get("EMAIL_CONTRASENA", "")
EMAIL_DESTINO    = os.environ.get("EMAIL_DESTINO", "")

SEEN_JOBS_FILE = "seen_jobs.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# Fuentes RSS con navegador real para evitar bloqueos
RSS_FEEDS = [
    # ZipRecruiter — Louisville KY (general)
    "https://www.ziprecruiter.com/jobs/feed?location=Louisville%2C+KY&search=",
    # ZipRecruiter — warehouse Louisville
    "https://www.ziprecruiter.com/jobs/feed?location=Louisville%2C+KY&search=warehouse",
    # ZipRecruiter — restaurant Louisville
    "https://www.ziprecruiter.com/jobs/feed?location=Louisville%2C+KY&search=restaurant",
    # ZipRecruiter — cleaning Louisville
    "https://www.ziprecruiter.com/jobs/feed?location=Louisville%2C+KY&search=cleaning",
    # Indeed con User-Agent de navegador
    "https://www.indeed.com/rss?q=&l=Louisville%2C+KY&sort=date",
    "https://www.indeed.com/rss?q=warehouse&l=Louisville%2C+KY&sort=date",
]


def cargar_vistos():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def guardar_vistos(vistos):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(vistos), f)


def fetch_feed(url):
    """Descarga RSS usando headers de navegador real para evitar bloqueos."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except Exception as e:
        print(f"  Error al descargar {url}: {e}")
        return None


def obtener_empleos():
    empleos = []
    for url in RSS_FEEDS:
        feed = fetch_feed(url)
        if not feed:
            continue
        count = len(feed.entries)
        print(f"  {url.split('?')[0]} → {count} empleos")
        for entry in feed.entries:
            empleos.append({
                "id":      entry.get("id") or entry.get("link", ""),
                "titulo":  entry.get("title", "Sin título"),
                "empresa": entry.get("author", "Empresa no especificada"),
                "link":    entry.get("link", ""),
                "fecha":   entry.get("published", ""),
            })
    return empleos


def enviar_email(nuevos):
    if not EMAIL_REMITENTE or not EMAIL_CONTRASENA or not EMAIL_DESTINO:
        print("ERROR: Faltan variables de entorno")
        return

    cuerpo_html = """
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
    <h2 style="color:#2563eb">🆕 Empleos Nuevos en Louisville, KY</h2>
    <p style="color:#6b7280">Se encontraron <strong>{count}</strong> empleos nuevos</p>
    """.format(count=len(nuevos))

    for job in nuevos[:20]:  # max 20 por email
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
        Alerta automática — Job Alert Louisville KY · {fecha}
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
        print(f"✅ Email enviado con {len(nuevos)} empleos nuevos a {EMAIL_DESTINO}")
    except Exception as e:
        print(f"❌ Error al enviar email: {e}")


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Revisando empleos en Louisville, KY...")

    vistos  = cargar_vistos()
    empleos = obtener_empleos()
    nuevos  = [j for j in empleos if j["id"] not in vistos]

    print(f"Total: {len(empleos)} empleos | Nuevos: {len(nuevos)}")

    if nuevos:
        enviar_email(nuevos)
        for j in nuevos:
            vistos.add(j["id"])
        guardar_vistos(vistos)
    else:
        print("No hay empleos nuevos.")


if __name__ == "__main__":
    main()
