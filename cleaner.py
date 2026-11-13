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
    
    # Reglas directas y efectivas para forzar la categorización:
    rules = [
        # 1. Limpieza de promociones antiguas (> 30 días)
        {"query": "category:promotions older_than:30d", "action": "trash"},
        
        # 2. Limpieza de Google Flights antiguos (> 10 días)
        {"query": 'from:flights older_than:10d', "action": "trash"},
        
        # 3. Limpieza de códigos OTP y verificación antiguos (> 3 días)
        {"query": 'subject:(OTP OR "código de verificación" OR "verification code" OR verification) older_than:3d', "action": "trash"},
        
        # 4. FINANZAS (Bancos, estados de cuenta, transferencias)
        {"query": 'from:(BBVA OR Chase OR Citibanamex OR Santander OR Amex OR PayPal OR Stripe OR Fidelity OR Wise OR "Mazda Financial") -category:promotions', "action": "label", "label": "Finanzas"},
        {"query": 'subject:(financiamiento OR préstamo OR credit OR statement OR transfer OR payment) -category:promotions', "action": "label", "label": "Finanzas"},
        
        # 5. LECTURA (Boletines, Espresso Matutino, Service95, Vanity Fair)
        {"query": 'from:(Service95 OR "Espresso Matutino") -category:promotions', "action": "label", "label": "Lectura"},
        {"query": 'subject:(newsletter OR boletín OR digest OR weekly OR monthly OR redemption) -statement -banco -category:promotions', "action": "label", "label": "Lectura"},
        
        # 6. VIAJES (Aeroméxico, Volaris, SpotHero, reservas)
        {"query": 'from:(Aeroméxico OR Volaris OR Viva OR SpotHero) -category:promotions', "action": "label", "label": "Viajes"},
        {"query": 'subject:(vuelo OR flight OR hotel OR reserva OR booking OR itinerary OR uber OR lyft OR bus OR parking) -category:promotions', "action": "label", "label": "Viajes"},
        
        # 7. COMPRAS (Factor75, Amazon, MercadoLibre)
        {"query": 'from:(Factor75 OR Amazon OR MercadoLibre) -category:promotions', "action": "label", "label": "Compras"},
        {"query": 'subject:(pedido OR order OR shipment OR package OR paquete OR box OR envío) -category:promotions', "action": "label", "label": "Compras"},
        
        # 8. EVENTOS (Conciertos, boletos)
        {"query": 'subject:(ticket OR boletos OR entrada OR concierto OR concert OR eventbrite OR ticketmaster OR show) -category:promotions', "action": "label", "label": "Eventos"}
    ]

    for rule in rules:
        if rule["action"] == "trash":
            process_query(service, rule["query"], "trash")
        elif rule["action"] == "label":
            process_query(service, rule["query"], "label", rule["label"])

if __name__ == '__main__':
    clean_inbox()
