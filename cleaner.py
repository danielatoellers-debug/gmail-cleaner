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

def process_query(service, query, action, target_label=None):
    full_query = f"in:inbox {query}"
    print(f"🔍 Buscando: [{full_query}]")
    
    response = service.users().messages().list(userId='me', q=full_query).execute()
    messages = response.get('messages', [])
    
    if not messages:
        return

    msg_ids = [msg['id'] for msg in messages]

    if action == 'trash':
        service.users().messages().batchDelete(userId='me', body={'ids': msg_ids}).execute()
        print(f"   ↳ 🗑️ {len(msg_ids)} mensajes enviados a la papelera.")
    
    elif action == 'label' and target_label:
        label_id = get_or_create_label(service, target_label)
        service.users().messages().batchModify(
            userId='me',
            body={'ids': msg_ids, 'addLabelIds': [label_id], 'removeLabelIds': ['INBOX']}
        ).execute()
        print(f"   ↳ ✨ {len(msg_ids)} mensajes etiquetados como '{target_label}' y archivados.")

def clean_inbox():
    print("🚀 Conectando a Gmail...")
    service = get_gmail_service()
    
    rules = [
        # 1. Limpieza de basura y promos antiguas
        {"query": "category:promotions older_than:30d", "action": "trash"},
        {"query": "from:flights older_than:10d", "action": "trash"},
        {"query": 'subject:(OTP OR "código de verificación" OR verification) older_than:3d', "action": "trash"},
        
        # 2. FINANZAS (Estrictamente transaccional, excluyendo promociones)
        {"query": "BBVA (statement OR estado OR pago OR transferencia OR cuenta OR corte OR compra OR cargo) -jingle -terror -promocion", "action": "label", "label": "Finanzas"},
        {"query": "Wise (transfer OR sent OR payment OR account OR password)", "action": "label", "label": "Finanzas"},
        {"query": "Mazda Financial (payment OR statement OR reminder OR due)", "action": "label", "label": "Finanzas"},
        {"query": "Chase (statement OR alert OR zelle OR transfer OR payment)", "action": "label", "label": "Finanzas"},
        {"query": "Fidelity Investments (statement OR confirmation OR transfer OR bill pay)", "action": "label", "label": "Finanzas"},
        {"query": "statement", "action": "label", "label": "Finanzas"},
        {"query": "financiamiento", "action": "label", "label": "Finanzas"},
        
        # 3. LECTURA
        {"query": "Espresso Matutino", "action": "label", "label": "Lectura"},
        {"query": "Service95", "action": "label", "label": "Lectura"},
        {"query": "newsletter", "action": "label", "label": "Lectura"},
        
        # 4. VIAJES
        {"query": "Aeroméxico (reservación OR vuelo OR boarding OR ticket) -promocion", "action": "label", "label": "Viajes"},
        {"query": "SpotHero", "action": "label", "label": "Viajes"},
        
        # 5. COMPRAS
        {"query": "Factor75", "action": "label", "label": "Compras"},
        {"query": "Amazon", "action": "label", "label": "Compras"},
        {"query": "MercadoLibre", "action": "label", "label": "Compras"},
        
        # 6. EVENTOS
        {"query": "ticketmaster", "action": "label", "label": "Eventos"}
    ]

    for rule in rules:
        try:
            if rule["action"] == "trash":
                process_query(service, rule["query"], "trash")
            elif rule["action"] == "label":
                process_query(service, rule["query"], "label", rule["label"])
        except Exception as e:
            print(f"❌ Error en regla: {e}")

if __name__ == '__main__':
    clean_inbox()
