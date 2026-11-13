import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def clean_inbox():
    creds = Credentials(
        token=os.environ.get('GMAIL_TOKEN'),
        refresh_token=os.environ.get('GMAIL_REFRESH_TOKEN'),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get('GMAIL_CLIENT_ID'),
        client_secret=os.environ.get('GMAIL_CLIENT_SECRET'),
    )

    service = build('gmail', 'v1', credentials=creds)

    # Regla: Buscar correos en promociones de más de 30 días
    query = "category:promotions older_than:30d"
    print(f"Buscando correos con la regla: {query}")

    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No se encontraron correos para limpiar hoy.")
        return

    print(f"Se encontraron {len(messages)} mensajes. Moviendo a la papelera...")
    
    msg_ids = [msg['id'] for msg in messages]
    
    service.users().messages().batchDelete(
        userId='me',
        body={'ids': msg_ids}
    ).execute()
    
    print("¡Limpieza completada con éxito!")

if __name__ == '__main__':
    clean_inbox()
