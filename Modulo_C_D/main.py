import os
import re
from datetime import datetime
from actions.email_actions import GmailClient
from actions.pdf_actions import PDFReader
from actions.excel_actions import ExcelManager

def extract_cpf_cep(text):
    """
    Extrai CPF e CEP do texto usando regex
    
    Args:
        text: Texto para extrair os dados
        
    Returns:
        dict: Dicionário com CPF e CEP encontrados
    """
    # Regex para CPF (formato: XXX.XXX.XXX-XX ou XXXXXXXXXXX)
    cpf_pattern = r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'
    
    # Regex para CEP (formato: XXXXX-XXX ou XXXXXXXX)
    cep_pattern = r'\b\d{5}-?\d{3}\b'
    
    cpf = re.search(cpf_pattern, text).group(0) if re.search(cpf_pattern, text) else None
    cep = re.search(cep_pattern, text).group(0) if re.search(cep_pattern, text) else None
    
    return {
        'cpf': cpf,
        'cep': cep
    }

def create_label(gmail_client, type_mail, date_str):
    """
    Cria a estrutura de pastas inbox/valid/YYYY-MM-DD
    
    Args:
        gmail_client: Cliente do Gmail
        date_str: Data no formato YYYY-MM-DD
        
    Returns:
        str: ID da pasta criada
    """
    folder_name = f"inbox/{type_mail}/{date_str}"
    
    # Verificar se a pasta já existe
    existing_labels = gmail_client.get_labels()
    for label in existing_labels:
        if label['name'] == folder_name:
            return label['id']
    
    # Criar a pasta se não existir
    return gmail_client.create_label(folder_name)

def process_emails():
    """
    Processa emails com 'Relatório diário' no assunto
    """
    # Inicializar cliente Gmail
    try:
        gmail = GmailClient()
    except Exception as e:
        print(f"Erro ao conectar com Gmail: {e}")
        return
    
    # Data atual
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Buscar emails com 'Relatório diário' no assunto (com ou sem acentuação) apenas da caixa de entrada
    query = 'in:inbox subject:(Relatório Diário OR "Relatorio Diario")'
    emails = gmail.search_emails(query, max_results=50)
    
    if not emails:
        print("Nenhum email com 'Relatório Diário' e anexos encontrado.")
        return
    
    print(f"Encontrados {len(emails)} emails com 'Relatório Diário' e anexos.")
    
   
    processed_count = 0
    
    for email_data in emails:
        try:
            email_id = email_data['id']
            sender = email_data['headers'].get('from', 'Remetente desconhecido')
            subject = email_data['headers'].get('subject', 'Sem assunto')
            
            print(f"\nProcessando email: {subject}")
            print(f"Remetente: {sender}")
        
            # Processar anexos PDF
            pdf_attachments = [att for att in email_data['attachments'] 
                             if att['mime_type'] == 'application/pdf']
            
            if pdf_attachments:
                print(f"Encontrados {len(pdf_attachments)} anexos PDF")
                
                # Criar pasta temporária para downloads
                temp_folder = f"temp_{current_date}"
                os.makedirs(temp_folder, exist_ok=True)
                
                for attachment in pdf_attachments:
                    try:
                        # Baixar anexo
                        filename = attachment['filename']
                        attachment_id = attachment['attachment_id']
                        
                        if attachment_id:
                            gmail.download_attachment(
                                email_id, 
                                attachment_id, 
                                filename, 
                                temp_folder
                            )
                            
                            # Ler PDF e extrair texto
                            pdf_path = os.path.join(temp_folder, filename)
                            if os.path.exists(pdf_path):
                                pdf_reader = PDFReader(pdf_path)
                                pdf_text = pdf_reader.extract_text()
                                
                                # Extrair CPF e CEP
                                extracted_data = extract_cpf_cep(pdf_text)
                                
                                print(f"Arquivo: {filename}")
                                print(f"CPF encontrado: {extracted_data['cpf']}")
                                print(f"CEP encontrado: {extracted_data['cep']}")
                            
                    except Exception as e:
                        print(f"Erro ao processar anexo {attachment['filename']}: {e}")
                
                    # Criar/inicializar arquivo Excel
                    excel_filename = f"dados_extraidos_{current_date}.xlsx"
                    excel_manager = ExcelManager(
                        os.path.abspath(excel_filename)
                    )

                    # Criar arquivo Excel com as colunas especificadas (apenas se não existir)
                    columns = ["Arquivo", "CPF", "CPF Válido", "CEP", "CEP Válido", "Erro"]
                    excel_manager.create_excel(columns)

                    if pdf_attachments:
                        # Validar CPF e CEP
                        cpf_valido = "Sim" if extracted_data['cpf'] else "Não"
                        cep_valido = "Sim" if extracted_data['cep'] else "Não"

                        erro = ""
                        if not extracted_data['cpf'] and not extracted_data['cep']:
                            erro = "CPF e CEP inválidos"
                            type_mail = "rejected"
                        elif not extracted_data['cpf']:
                            erro = "CPF inválido"
                            type_mail = "rejected"
                        elif not extracted_data['cep']:
                            erro = "CEP inválido"
                            type_mail = "rejected"
                        else:
                            erro = "N/A"
                            type_mail = "valid"
                    else:
                        erro = "Nenhum anexo PDF encontrado"
                        type_mail = "rejected"

                    # Adicionar dados ao Excel
                    row_data = [
                        filename,
                        extracted_data['cpf'] or "N/A",
                        cpf_valido,
                        extracted_data['cep'] or "N/A", 
                        cep_valido,
                        erro
                    ]
                    excel_manager.append_row(row_data)

                try:
                    os.rmdir(temp_folder)
                except:
                    pass
            else:
                print("Nenhum anexo PDF encontrado neste email.")
                type_mail = "rejected"
            processed_count += 1

            if type_mail == "valid":
                print("Email classificado como válido.")
                template = 'actions/email_template_valido.html'
                
            else:
                print("Email classificado como inválido.")
                template = 'actions/email_template_invalido.html'
            # Responder ao remetente
            reply_subject = f"Re: {subject}"
            
            # Ler o corpo do email de um arquivo HTML
            try:
                with open(template, 'r', encoding='utf-8') as f:
                    reply_body = f.read()
                
                # Substituir placeholders no template
                reply_body = reply_body.replace('{DATE}', datetime.now().strftime("%d/%m/%Y às %H:%M"))
            except FileNotFoundError:
                raise Exception("Template de email não encontrado.")
            
            # Extrair email do remetente
            sender_email = re.search(r'<(.+?)>', sender)
            if sender_email:
                sender_email = sender_email.group(1)
            else:
                sender_email = sender.strip()
            
            # Enviar email de resposta
            gmail.send_email(
                to=sender_email,
                subject=reply_subject,
                body=reply_body,
                is_html=True
            )

            # Criar estrutura de pastas
            folder_id = create_label(gmail, type_mail, current_date)
            if not folder_id:
                print("Erro ao criar pasta. Abortando processamento.")
                return
            # Mover email para pasta
            gmail.move_email_to_label(email_id, folder_id)
        except Exception as e:
            print(f"Erro ao processar email {email_data.get('id', 'ID desconhecido')}: {e}")
    
    print(f"\nProcessamento concluído. {processed_count} email(s) processado(s).")

if __name__ == "__main__":
    process_emails()
