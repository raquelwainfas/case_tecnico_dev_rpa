import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GmailClient:
    """Cliente para interação com Gmail usando Google API"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.labels',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        """
        Inicializa o cliente Gmail
        
        Args:
            credentials_file: Caminho para o arquivo de credenciais OAuth2
            token_file: Caminho para o arquivo de token de acesso
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Autentica com a API do Gmail"""
        creds = None
        
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
    
    def search_emails(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Busca emails baseado em filtros
        
        Args:
            query: Query de busca (ex: 'from:example@gmail.com has:attachment')
            max_results: Número máximo de resultados
            
        Returns:
            Lista de emails encontrados
        """
        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                email_data = self._get_email_details(message['id'])
                emails.append(email_data)
            
            return emails
            
        except HttpError as error:
            print(f'Erro ao buscar emails: {error}')
            return []
    
    def _get_email_details(self, message_id: str) -> Dict[str, Any]:
        """Obtém detalhes completos de um email"""
        try:
            message = self.service.users().messages().get(
                userId='me', id=message_id, format='full'
            ).execute()
            
            payload = message['payload']
            headers = payload.get('headers', [])
            
            # Extrair informações básicas
            email_data = {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'label_ids': message.get('labelIds', []),
                'snippet': message.get('snippet', ''),
                'attachments': [],
                'body': '',
                'headers': {}
            }
            
            # Processar headers
            for header in headers:
                name = header['name'].lower()
                email_data['headers'][name] = header['value']
            
            # Processar corpo e anexos
            self._process_message_parts(payload, email_data)
            
            return email_data
            
        except HttpError as error:
            print(f'Erro ao obter detalhes do email: {error}')
            return {}
    
    def _process_message_parts(self, payload: Dict, email_data: Dict):
        """Processa as partes do email (corpo e anexos)"""
        if 'parts' in payload:
            for part in payload['parts']:
                self._process_message_parts(part, email_data)
        else:
            mime_type = payload.get('mimeType', '')
            filename = payload.get('filename', '')
            
            if filename:  # É um anexo
                attachment_data = {
                    'filename': filename,
                    'mime_type': mime_type,
                    'size': payload.get('body', {}).get('size', 0),
                    'attachment_id': payload.get('body', {}).get('attachmentId')
                }
                email_data['attachments'].append(attachment_data)
            
            elif mime_type == 'text/plain' or mime_type == 'text/html':
                body_data = payload.get('body', {}).get('data', '')
                if body_data:
                    decoded_body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                    email_data['body'] += decoded_body
    
    def download_attachment(self, message_id: str, attachment_id: str, filename: str, save_path: str = '.'):
        """
        Baixa um anexo de email
        
        Args:
            message_id: ID da mensagem
            attachment_id: ID do anexo
            filename: Nome do arquivo
            save_path: Caminho para salvar o arquivo
        """
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me', messageId=message_id, id=attachment_id
            ).execute()
            
            file_data = base64.urlsafe_b64decode(attachment['data'])
            file_path = os.path.join(save_path, filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            print(f'Anexo baixado: {file_path}')
            
        except HttpError as error:
            print(f'Erro ao baixar anexo: {error}')
    
    def send_email(self, to: str, subject: str, body: str, 
                   attachments: Optional[List[str]] = None, 
                   cc: Optional[str] = None, 
                   bcc: Optional[str] = None,
                   is_html: bool = False):
        """
        Envia um email
        
        Args:
            to: Destinatário
            subject: Assunto
            body: Corpo do email
            attachments: Lista de caminhos de arquivos para anexar
            cc: Cópia
            bcc: Cópia oculta
            is_html: Se True, o corpo será formatado como HTML, caso contrário como texto plano
        """
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Definir tipo de conteúdo baseado no parâmetro is_html
            content_type = 'html' if is_html else 'plain'
            message.attach(MIMEText(body, content_type))
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            send_message = self.service.users().messages().send(
                userId='me', body={'raw': raw_message}
            ).execute()
            
            print(f'Email enviado com ID: {send_message["id"]}')
            return send_message
            
        except HttpError as error:
            print(f'Erro ao enviar email: {error}')
            return None
    
    def create_label(self, label_name: str) -> Optional[str]:
        """
        Cria uma nova pasta (label) no Gmail
        
        Args:
            label_name: Nome da pasta/label
            
        Returns:
            ID da label criada ou None se houver erro
        """
        try:
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            
            created_label = self.service.users().labels().create(
                userId='me', body=label_object
            ).execute()
            
            print(f'Pasta criada: {label_name} (ID: {created_label["id"]})')
            return created_label['id']
            
        except HttpError as error:
            print(f'Erro ao criar pasta: {error}')
            return None
    
    def get_labels(self) -> List[Dict[str, str]]:
        """Obtém todas as pastas/labels disponíveis"""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            return [{'id': label['id'], 'name': label['name']} for label in labels]
            
        except HttpError as error:
            print(f'Erro ao obter pastas: {error}')
            return []
    
    def move_email_to_label(self, message_id: str, label_id: str, remove_inbox: bool = True):
        """
        Move email para uma pasta específica
        
        Args:
            message_id: ID da mensagem
            label_id: ID da pasta de destino
            remove_inbox: Se deve remover da caixa de entrada
        """
        try:
            labels_to_add = [label_id]
            labels_to_remove = ['INBOX'] if remove_inbox else []
            
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': labels_to_add,
                    'removeLabelIds': labels_to_remove
                }
            ).execute()
            
            print(f'Email {message_id} movido para pasta {label_id}')
            
        except HttpError as error:
            print(f'Erro ao mover email: {error}')
    
