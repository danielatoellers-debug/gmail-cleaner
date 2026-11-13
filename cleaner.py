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
    # Busca si la etiqueta ya existe
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    for label in labels:
        if label['name'].lower() == label_name.lower():
            return label['id']
    
    # Si no existe, la crea
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
    
    # Definimos tus reglas de limpieza y organización personalizadas:
    rules = [
        # 1. Borrar promociones de más de 30 días
        {"query": "category:promotions older_than:30d", "action": "trash"},
        
        # 2. Borrar códigos OTP y de verificación viejos (más de 3 días para evitar que fallen si los buscas recién llegado)
        {"query": 'subject:(OTP OR "código de verificación" OR "verification code" OR "two-factor" OR "autenticación") older_than:3d', "action": "trash"},
        
        # 3. Organizar correos de bancos/finanzas en una carpeta "Finanzas"
        {"query": 'from:(banco OR bbva OR chase OR citibanamex OR santander OR amex OR paypal OR stripe OR fidelity) -category:promotions', "action": "label", "label": "Finanzas"}
    ]

    for rule in rules:
        if rule["action"] == "trash":
            process_query(service, rule["query"], "trash")
        elif rule["action"] == "label":
            process_query(service, rule["query"], "label", rule["label"])

if __name__ == '__main__':
    clean_inbox()
