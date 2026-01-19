# Desafio RPA – Automação de Processamento de Informações

## Visão Geral

Este repositório contém a implementação de uma solução de **Automação Robótica de Processos (RPA)** desenvolvida para automatizar a coleta, processamento e consolidação de informações provenientes de múltiplas fontes, como web, e-mails, documentos PDF e APIs públicas.

A solução foi construída utilizando **UiPath e Python**, com foco em boas práticas de desenvolvimento, resiliência, observabilidade, escalabilidade e facilidade de manutenção. O fluxo automatizado contempla desde a ingestão e normalização de dados até a geração de relatórios estruturados e publicação de informações em filas para processamento assíncrono.

O processamento foi dividido em **cinco módulos independentes**, que se comunicam principalmente por meio de **Queues do UiPath Orchestrator**, permitindo desacoplamento, controle de execução, reprocessamento e rastreabilidade ponta a ponta.

---

## Arquitetura da Solução

A arquitetura segue o padrão **Dispatcher / Performer**, além de módulos independentes para ingestão de e-mails, processamento de documentos e consumo de API.
<img width="3592" height="1990" alt="diagrama_mermaid" src="https://github.com/user-attachments/assets/d6a3db55-968e-4441-9681-7ced291e783a" />

---

## Descrição dos Módulos

### 🔹 Módulo A — Coleta Web & Normalização (UiPath | Dispatcher)

- Realiza web scraping no site: https://news.yahoo.com
- Extrai as 5 primeiras notícias do bloco **"Stories for you"**
- Normaliza os dados (remoção de caracteres inválidos e padronização)
- Gera o arquivo `news_raw_<DATA>.csv` com os campos:
  - `titulo`
  - `resumo`
  - `tema`
  - `fonte`
  - `tempo_leitura`
- Publica os itens em **Queues do Orchestrator**

---

### 🔹 Módulo B — Sistema de Newsletter (UiPath | Performer)

- Consome os itens publicados pelo Módulo A
- Direciona cada notícia para grupos de e-mail com base no tema
- Grupos de e-mail armazenados fora do código (Assets, arquivo Config.xlsx)
- Estrutura preparada para fácil manutenção e expansão

---

### 🔹 Módulo C — Ingestão de E-mails & Anexos (Python)

- Leitura da caixa de e-mails
- Identificação de mensagens com assunto **"Relatório Diário"**
- Salvamento de PDFs válidos em `inbox/valid/YYYY-MM-DD/`
- Confirmação automática de recebimento
- Controle de duplicidade e idempotência
- Tratamento e segregação de e-mails inválidos em `inbox/rejected/YYYY-MM-DD/`

---

### 🔹 Módulo D — Extração de Dados de PDF (Python)

- Processamento de PDFs válidos
- Extração de CPF e CEP via regex
- Validação de formato e dígitos verificadores
- Geração do arquivo `dados_extraidos_<DATA>.xlsx`

📌 Os módulos C e D são integrados em uma única aplicação Python, composta por múltiplas classes e uma `main.py`.

---

### 🔹 Módulo E — Consumo de API Pública (UiPath | Independente)

- Consumo da API pública CoinGecko
- Extração das 5 maiores criptomoedas
- Geração do arquivo `coins_<DATA>.csv`
- Publicação em Queue
- Coleta de métricas e tratamento de falhas com retry/backoff
- Garantia de idempotência

---

## Requisitos Transversais

- Logs estruturados em JSON
- Métricas consolidadas por execução
- Tratamento de exceções e resiliência
- Idempotência e reprocessamento controlado
- Configurações externas ao código

---

## Execução

### UiPath
1. Importar projetos no UiPath Studio
2. Configurar Assets, Queues e credenciais
3. Publicar no Orchestrator
4. Executar conforme necessidade

### Python
1. Criar um ambiente virtual `.venv`
```bash
cd /caminho/para/seu/projeto
python -m venv venv
```
2. Ativar o ambiente virtual criado

*No Windows*
```bash
.\venv\Scripts\activate
```
*No macOS/Linux*
```bash
source venv/bin/activate
```
3. Instalar as bibliotecas listadas no `requirements.txt` e executar o script
```bash
pip install -r requirements.txt
python main.py
```
