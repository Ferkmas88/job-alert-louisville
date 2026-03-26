import os
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- Config ---
EMAIL_REMITENTE   = os.environ.get("EMAIL_REMITENTE", "")
EMAIL_CONTRASENA  = os.environ.get("EMAIL_CONTRASENA", "")
EMAIL_DESTINO     = os.environ.get("EMAIL_DESTINO", "")
ADZUNA_APP_ID     = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY    = os.environ.get("ADZUNA_APP_KEY", "")

SEEN_JOBS_FILE = "seen_jobs.json"

# Tipos de trabajo a buscar en Louisville KY
BUSQUEDAS = [
    "",             # todos los empleos
    "warehouse",
    "restaurant",
    "cleaning",
    "construction",
    "driver",
    "amazon",
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
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("ERROR: Faltan ADZUNA_APP_ID o ADZUNA_APP_KEY")
        return []

    empleos = []
    for query in BUSQUEDAS:
        url = (
            f"https://api.adzuna.com/v1/api/jobs/us/search/1"
            f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}"
            f"&where=Louisville%2C+KY"
            f"&what={query}"
            f"&results_per_page=20"
            f"&sort_by=date"
            f"&max_days_old=1"
        )
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            print(f"  '{query or 'todos'}' → {len(results)} empleos")
            for job in results:
                empleos.append({
                    "id":      str(job.get("id", "")),
                    "titulo":  job.get("title", "Sin título"),
                    "empresa": job.get("company", {}).get("display_name", "Empresa no especificada"),
                    "link":    job.get("redirect_url", ""),
                    "salario": job.get("salary_min", ""),
                })
        except Exception as e:
            print(f"  Error en búsqueda '{query}': {e}")

    # Eliminar duplicados por id
    vistos_ids = set()
    unicos = []
    for j in empleos:
        if j["id"] not in vistos_ids:
            vistos_ids.add(j["id"])
            unicos.append(j)
    return unicos


def enviar_email(nuevos):
    if not EMAIL_REMITENTE or not EMAIL_CONTRASENA or not EMAIL_DESTINO:
        print("ERROR: Faltan variables de email")
        return

    cuerpo_html = """
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
    <h2 style="color:#2563eb">🆕 Empleos Nuevos en Louisville, KY</h2>
    <p style="color:#6b7280"><strong>{count}</strong> empleos nuevos encontrados hoy</p>
    """.format(count=len(nuevos))

    for job in nuevos[:25]:
        salario = f"💰 ${job['salario']:,.0f}/yr" if job.get("salario") else ""
        cuerpo_html += """
        <div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin:12px 0">
            <h3 style="margin:0 0 4px;color:#111827">{titulo}</h3>
            <p style="margin:0 0 4px;color:#6b7280;font-size:14px">🏢 {empresa} {salario}</p>
            <a href="{link}" style="background:#2563eb;color:white;padding:8px 16px;
               border-radius:4px;text-decoration:none;font-size:14px">Ver empleo →</a>
        </div>
        """.format(**job, salario=salario)

    cuerpo_html += """
    <p style="color:#9ca3af;font-size:12px;margin-top:24px">
        Job Alert Louisville KY · {fecha}
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
        print(f"✅ Email enviado: {len(nuevos)} empleos a {EMAIL_DESTINO}")
    except Exception as e:
        print(f"❌ Error email: {e}")


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Revisando empleos Louisville, KY...")

    vistos  = cargar_vistos()
    empleos = obtener_empleos()
    nuevos  = [j for j in empleos if j["id"] not in vistos]

    print(f"Total únicos: {len(empleos)} | Nuevos: {len(nuevos)}")

    if nuevos:
        enviar_email(nuevos)
        for j in nuevos:
            vistos.add(j["id"])
        guardar_vistos(vistos)
    else:
        print("No hay empleos nuevos.")


if __name__ == "__main__":
    main()
