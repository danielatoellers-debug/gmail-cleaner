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
    
    label_object = {'name': label_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
    created_label = service.users().labels().create(userId='me', body=label_object).execute()
    return created_label['id']

def process_query(service, query, action, target_label=None):
    print(f"Buscando con la regla: {query}")
    try:
        response = service.users().messages().list(userId='me', q=query).execute()
        messages = response.get('messages', [])
        
        if not messages:
            print("No se encontraron mensajes para esta regla.")
            return

        msg_ids = [msg['id'] for msg in messages]
        print(f"Se encontraron {len(msg_ids)} mensajes.")

        if action == 'trash':
            service.users().messages().batchDelete(userId='me', body={'ids': msg_ids}).execute()
            print("-> Mensajes enviados a la papelera con éxito.")
        
        elif action == 'label' and target_label:
            label_id = get_or_create_label(service, target_label)
            service.users().messages().batchModify(
                userId='me',
                body={'ids': msg_ids, 'addLabelIds': [label_id], 'removeLabelIds': ['INBOX']}
            ).execute()
            print(f"-> Mensajes movidos a la etiqueta/carpeta '{target_label}' y archivados de la bandeja principal.")

    except Exception as e:
        print(f"Error procesando la regla '{query}': {e}")

def clean_inbox():
    service = get_gmail_service()
    
    # Reglas directas basadas en los remitentes exactos que tienes en tu bandeja:
    rules = [
        # 1. Limpieza de promociones y Google Flights viejos
        {"query": "category:promotions older_than:30d", "action": "trash"},
        {"query": "from:flights older_than:10d", "action": "trash"},
        {"query": 'subject:(OTP OR "código de verificación" OR verification) older_than:3d', "action": "trash"},
        
        # 2. FINANZAS (BBVA, Wise, Mazda Financial, Chase, etc.)
        {"query": "BBVA", "action": "label", "label": "Finanzas"},
        {"query": "Wise", "action": "label", "label": "Finanzas"},
        {"query": "Mazda Financial", "action": "label", "label": "Finanzas"},
        {"query": "Chase", "action": "label", "label": "Finanzas"},
        {"query": "statement", "action": "label", "label": "Finanzas"},
        {"query": "financiamiento", "action": "label", "label": "Finanzas"},
        
        # 3. LECTURA (Espresso Matutino, Service95, Vanity Fair)
        {"query": "Espresso Matutino", "action": "label", "label": "Lectura"},
        {"query": "Service95", "action": "label", "label": "Lectura"},
        {"query": "Vanity Fair", "action": "label", "label": "Lectura"},
        {"query": "newsletter", "action": "label", "label": "Lectura"},
        
        # 4. VIAJES (Aeroméxico, SpotHero)
        {"query": "Aeroméxico", "action": "label", "label": "Viajes"},
        {"query": "SpotHero", "action": "label", "label": "Viajes"},
        {"query": "vuelo", "action": "label", "label": "Viajes"},
        
        # 5. COMPRAS (Factor75, Amazon, MercadoLibre)
        {"query": "Factor75", "action": "label", "label": "Viajes"}, # O compras:
        {"query": "Factor75", "action": "label", "label": "Compras"},
        {"query": "Amazon", "action": "label", "label": "Compras"},
        {"query": "MercadoLibre", "action": "label", "label": "Compras"},
        {"query": "pedido", "action": "label", "label": "Compras"},
        
        # 6. EVENTOS
        {"query": "ticketmaster", "action": "label", "label": "Eventos"},
        {"query": "concierto", "action": "label", "label": "Eventos"}
    ]

    for rule in rules:
        if rule["action"] == "trash":
            process_query(service, rule["query"], "trash")
        elif rule["action"] == "label":
            process_query(service, rule["query"], "label", rule["label"])

if __name__ == '__main__':
    clean_inbox()
