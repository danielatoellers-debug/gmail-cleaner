import os
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_gmail_service():
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    token = os.environ.get("GMAIL_TOKEN")

    creds = Credentials(
        token=token,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build('gmail', 'v1', credentials=creds)

def get_or_create_label(service, label_name):
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    for label in labels:
        if label['name'].lower() == label_name.lower():
            return label['id']
    
    print(f"🏷️ Creando etiqueta: {label_name}")
    label_object = {'name': label_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
    created_label = service.users().labels().create(userId='me', body=label_object).execute()
    return created_label['id']

def clean_inbox():
    print("🚀 Conectando a Gmail...")
    service = get_gmail_service()
    
    # 1. Vamos a listar los primeros 10 mensajes actuales del Inbox para probar la conexión real
    print("\n--- DIAGNÓSTICO DEL INBOX ---")
    results = service.users().messages().list(userId='me', q="in:inbox", maxResults=10).execute()
    messages = results.get('messages', [])
    
    if not messages:
        print("⚠️ El script no encontró ningún mensaje en el Inbox.")
    else:
        print(f"✅ Se leyeron {len(messages)} mensajes del Inbox correctamente.")
        for msg in messages:
            msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From']).execute()
            headers = msg_detail.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sin asunto')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconocido')
            print(f"   - De: {sender} | Asunto: {subject}")

    print("\n--- APLICANDO REGLAS ---")
    
    # Reglas simplificadas para probar etiquetas directas
    rules = [
        {"query": "BBVA", "label": "Finanzas"},
        {"query": "Wise", "label": "Finanzas"},
        {"query": "Mazda", "label": "Finanzas"},
        {"query": "Espresso Matutino", "label": "Lectura"},
        {"query": "Factor75", "label": "Compras"},
        {"query": "Aeroméxico", "label": "Viajes"}
    ]

    for rule in rules:
        q = f"in:inbox {rule['query']}"
        print(f"Buscando: [{q}]")
        res = service.users().messages().list(userId='me', q=q).execute()
        msgs = res.get('messages', [])
        
        if msgs:
            msg_ids = [m['id'] for m in msgs]
            print(f" -> ¡Encontrados {len(msg_ids)} mensajes para '{rule['query']}'!")
            try:
                label_id = get_or_create_label(service, rule['label'])
                service.users().messages().batchModify(
                    userId='me',
                    body={'ids': msg_ids, 'addLabelIds': [label_id], 'removeLabelIds': ['INBOX']}
                ).execute( )
                print(f" -> ✨ ¡Movidos exitosamente a '{rule['label']}'!")
            except Exception as e:
                print(f" ❌ ERROR al modificar mensajes (¿Faltan permisos de escritura en el token?): {e}")
        else:
            print(" -> Sin coincidencias.")

if __name__ == '__main__':
    clean_inbox()
