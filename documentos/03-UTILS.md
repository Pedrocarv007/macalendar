# Utilitários - MAC Calendar

## Sumário

- [Email (app/utils/email.py)](#email)
- [Document Generator (app/utils/document_generator.py)](#document-generator)
- [Helpers (app/utils/helpers.py)](#helpers)

---

## Email

### Descrição
Módulo para envio de emails usando SMTP (Gmail). Suporta envio assíncrono para não bloquear requests.

### Configuração

Variáveis de ambiente necessárias:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-de-app
MAIL_DEFAULT_SENDER=seu-email@gmail.com
```

**Nota:** Para Gmail, criar "App Password" em: https://myaccount.google.com/apppasswords

---

### Funções

#### `send_email_async(subject: str, recipient: str, body_html: str, app: Flask) -> None`
Envia email de forma assíncrona.

**Parâmetros:**
- `subject`: Assunto do email
- `recipient`: Email do destinatário
- `body_html`: Corpo do email em HTML
- `app`: Instância do Flask app (para contexto)

**Exemplo:**
```python
from app.utils.email import send_email_async
from flask import current_app

subject = "Bem-vindo ao MAC Calendar"
recipient = "novo@example.com"
body_html = """
<html>
  <body>
    <h1>Bem-vindo!</h1>
    <p>Suas credenciais de acesso:</p>
    <ul>
      <li>Email: novo@example.com</li>
      <li>Senha temporária: Temp123!</li>
    </ul>
  </body>
</html>
"""

send_email_async(subject, recipient, body_html, current_app._get_current_object())
```

**Comportamento:**
- Executa em thread separada (não bloqueia request)
- Usa SSL/TLS para segurança
- Loga erros sem quebrar aplicação
- Timeout de 30 segundos

---

#### `send_welcome_email(employee_email: str, employee_name: str, temp_password: str, app: Flask) -> None`
Envia email de boas-vindas para novo colaborador.

**Parâmetros:**
- `employee_email`: Email do colaborador
- `employee_name`: Nome do colaborador
- `temp_password`: Senha temporária gerada
- `app`: Instância do Flask app

**Exemplo:**
```python
from app.utils.email import send_welcome_email
from flask import current_app

send_welcome_email(
    employee_email="maria@example.com",
    employee_name="Maria Santos",
    temp_password="TempPass123!",
    app=current_app._get_current_object()
)
```

**Template HTML:**
```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { background: #007bff; color: white; padding: 20px; }
        .content { padding: 20px; }
        .button { background: #28a745; color: white; padding: 10px 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Bem-vindo ao MAC Calendar</h1>
        </div>
        <div class="content">
            <p>Olá %(name)s,</p>
            <p>Suas credenciais de acesso:</p>
            <ul>
                <li><strong>Email:</strong> %(email)s</li>
                <li><strong>Senha temporária:</strong> %(password)s</li>
            </ul>
            <p>Acesse: <a href="%(login_url)s">%(login_url)s</a></p>
        </div>
    </div>
</body>
</html>
```

---

#### `send_password_reset_email(user_email: str, reset_token: str, app: Flask) -> None`
Envia email de recuperação de senha.

**Parâmetros:**
- `user_email`: Email do usuário
- `reset_token`: Token de reset (JWT)
- `app`: Instância do Flask app

**Exemplo:**
```python
from app.utils.email import send_password_reset_email
from flask import current_app
import jwt
from datetime import datetime, timedelta

# Gerar token
reset_token = jwt.encode(
    {'user_id': user.id, 'exp': datetime.utcnow() + timedelta(hours=1)},
    current_app.config['SECRET_KEY'],
    algorithm='HS256'
)

send_password_reset_email(
    user_email="usuario@example.com",
    reset_token=reset_token,
    app=current_app._get_current_object()
)
```

---

### Tratamento de Erros

```python
import logging

try:
    send_email_async(subject, recipient, body_html, app)
except Exception as e:
    logging.error(f"Erro ao enviar email: {str(e)}")
    # Aplicação continua funcionando
```

---

### Testing

Para testar envio de emails sem enviar de verdade:

```python
# Em config/settings.py (desenvolvimento)
MAIL_SUPPRESS_SEND = True  # Não envia emails reais
TESTING = True

# Usar Flask-Mail testing
with mail.record_messages() as outbox:
    send_welcome_email(...)
    assert len(outbox) == 1
    assert "Bem-vindo" in outbox[0].subject
```

---

## Document Generator

### Descrição
Módulo para geração de documentos PDF (relatórios, contratos, folhas de ponto) usando ReportLab.

### Dependência
```bash
pip install reportlab
```

---

### Funções

#### `generate_employee_report(employee: Employee, output_path: str) -> str`
Gera relatório em PDF com dados do colaborador.

**Parâmetros:**
- `employee`: Objeto Employee
- `output_path`: Caminho onde salvar o PDF

**Retorno:** Caminho do arquivo gerado

**Exemplo:**
```python
from app.utils.document_generator import generate_employee_report
from app.models.employee import Employee

employee = Employee.query.get(1)
pdf_path = generate_employee_report(
    employee=employee,
    output_path="uploads/generated/employee_1_report.pdf"
)

print(f"Relatório gerado: {pdf_path}")
```

**Conteúdo do PDF:**
- Cabeçalho com logo da empresa
- Dados pessoais do colaborador
- Dados profissionais (cargo, departamento, restaurante)
- Data de contratação e tempo de casa
- Foto (se disponível)

---

#### `generate_timesheet(employee: Employee, month: int, year: int, output_path: str) -> str`
Gera folha de ponto mensal em PDF.

**Parâmetros:**
- `employee`: Objeto Employee
- `month`: Mês (1-12)
- `year`: Ano (ex: 2024)
- `output_path`: Caminho onde salvar

**Retorno:** Caminho do arquivo gerado

**Exemplo:**
```python
from app.utils.document_generator import generate_timesheet
from datetime import datetime

employee = Employee.query.get(1)
current_month = datetime.now().month
current_year = datetime.now().year

pdf_path = generate_timesheet(
    employee=employee,
    month=current_month,
    year=current_year,
    output_path=f"uploads/generated/timesheet_{employee.id}_{current_month}.pdf"
)
```

**Conteúdo do PDF:**
- Tabela com todos os dias do mês
- Colunas: Data, Entrada, Saída, Total de Horas
- Resumo mensal (horas trabalhadas, faltas, etc.)

---

#### `generate_contract(employee: Employee, contract_type: str, output_path: str) -> str`
Gera contrato de trabalho em PDF.

**Parâmetros:**
- `employee`: Objeto Employee
- `contract_type`: Tipo de contrato ('permanent', 'temporary', 'internship')
- `output_path`: Caminho onde salvar

**Retorno:** Caminho do arquivo gerado

**Exemplo:**
```python
from app.utils.document_generator import generate_contract

employee = Employee.query.get(1)
pdf_path = generate_contract(
    employee=employee,
    contract_type='permanent',
    output_path=f"uploads/generated/contract_{employee.id}.pdf"
)
```

---

### Customização de PDFs

#### Adicionar logo:
```python
from reportlab.lib.utils import ImageReader

logo = ImageReader('app/static/images/logo.png')
pdf.drawImage(logo, x=50, y=750, width=100, height=50)
```

#### Estilos de texto:
```python
from reportlab.lib.styles import getSampleStyleSheet

styles = getSampleStyleSheet()
title_style = styles['Title']
normal_style = styles['Normal']
```

#### Tabelas:
```python
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

data = [
    ['Data', 'Entrada', 'Saída', 'Total'],
    ['01/12/2024', '09:00', '18:00', '8h'],
    ['02/12/2024', '09:00', '18:00', '8h'],
]

table = Table(data)
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('GRID', (0, 0), (-1, -1), 1, colors.black)
]))
```

---

## Helpers

### Descrição
Funções auxiliares gerais usadas em toda aplicação.

---

### Funções

#### `generate_temp_password(length: int = 12) -> str`
Gera senha temporária segura.

**Parâmetros:**
- `length`: Tamanho da senha (padrão: 12)

**Retorno:** String com senha aleatória

**Exemplo:**
```python
from app.utils.helpers import generate_temp_password

password = generate_temp_password(16)
print(password)  # Ex: "Kd9#mP2@xL5!nQ8v"
```

**Características:**
- Inclui maiúsculas, minúsculas, números e caracteres especiais
- Garantia de pelo menos um de cada tipo
- Embaralhamento aleatório

---

#### `validate_password_strength(password: str) -> tuple[bool, str]`
Valida força da senha.

**Parâmetros:**
- `password`: Senha a validar

**Retorno:** Tupla (é_válida, mensagem_erro)

**Exemplo:**
```python
from app.utils.helpers import validate_password_strength

is_valid, message = validate_password_strength("123456")
if not is_valid:
    print(f"Senha fraca: {message}")
    # Output: "Senha fraca: Senha deve ter pelo menos 8 caracteres"

is_valid, message = validate_password_strength("SenhaForte123!")
print(is_valid)  # True
```

**Regras:**
- Mínimo 8 caracteres
- Pelo menos uma maiúscula
- Pelo menos uma minúscula
- Pelo menos um número
- Pelo menos um caractere especial

---

#### `format_phone(phone: str) -> str`
Formata número de telefone para padrão +351 XXX XXX XXX.

**Parâmetros:**
- `phone`: Telefone a formatar

**Retorno:** Telefone formatado

**Exemplo:**
```python
from app.utils.helpers import format_phone

phone = format_phone("912345678")
print(phone)  # "+351 912 345 678"

phone = format_phone("+351912345678")
print(phone)  # "+351 912 345 678"
```

---

#### `calculate_age(birth_date: date) -> int`
Calcula idade a partir da data de nascimento.

**Parâmetros:**
- `birth_date`: Data de nascimento

**Retorno:** Idade em anos

**Exemplo:**
```python
from app.utils.helpers import calculate_age
from datetime import date

birth = date(1990, 5, 15)
age = calculate_age(birth)
print(age)  # Ex: 34
```

---

#### `calculate_work_years(hire_date: date) -> float`
Calcula anos de trabalho (tempo de casa).

**Parâmetros:**
- `hire_date`: Data de contratação

**Retorno:** Anos trabalhados (com decimais)

**Exemplo:**
```python
from app.utils.helpers import calculate_work_years
from datetime import date

hire = date(2020, 1, 10)
years = calculate_work_years(hire)
print(f"{years:.1f} anos")  # Ex: "4.9 anos"
```

---

#### `days_until_birthday(birth_date: date) -> int`
Calcula dias até próximo aniversário.

**Parâmetros:**
- `birth_date`: Data de nascimento

**Retorno:** Número de dias

**Exemplo:**
```python
from app.utils.helpers import days_until_birthday
from datetime import date

birth = date(1990, 12, 25)
days = days_until_birthday(birth)
print(f"Faltam {days} dias")  # Ex: "Faltam 7 dias"
```

---

#### `sanitize_filename(filename: str) -> str`
Remove caracteres perigosos de nome de arquivo.

**Parâmetros:**
- `filename`: Nome original do arquivo

**Retorno:** Nome sanitizado

**Exemplo:**
```python
from app.utils.helpers import sanitize_filename

safe_name = sanitize_filename("../../../etc/passwd")
print(safe_name)  # "etcpasswd"

safe_name = sanitize_filename("Relatório (Dez/2024).pdf")
print(safe_name)  # "Relatorio_Dez_2024.pdf"
```

---

#### `allowed_file(filename: str, allowed_extensions: set) -> bool`
Verifica se extensão do arquivo é permitida.

**Parâmetros:**
- `filename`: Nome do arquivo
- `allowed_extensions`: Set de extensões permitidas

**Retorno:** True se permitido

**Exemplo:**
```python
from app.utils.helpers import allowed_file

ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_DOCS = {'pdf', 'doc', 'docx'}

is_valid = allowed_file('photo.jpg', ALLOWED_IMAGES)
print(is_valid)  # True

is_valid = allowed_file('malware.exe', ALLOWED_IMAGES)
print(is_valid)  # False
```

---

#### `get_file_extension(filename: str) -> str`
Extrai extensão do arquivo.

**Parâmetros:**
- `filename`: Nome do arquivo

**Retorno:** Extensão em minúsculas (sem ponto)

**Exemplo:**
```python
from app.utils.helpers import get_file_extension

ext = get_file_extension('document.PDF')
print(ext)  # "pdf"

ext = get_file_extension('photo.jpeg')
print(ext)  # "jpeg"
```

---

#### `format_file_size(size_bytes: int) -> str`
Formata tamanho de arquivo para leitura humana.

**Parâmetros:**
- `size_bytes`: Tamanho em bytes

**Retorno:** String formatada

**Exemplo:**
```python
from app.utils.helpers import format_file_size

size = format_file_size(1024)
print(size)  # "1.0 KB"

size = format_file_size(1048576)
print(size)  # "1.0 MB"

size = format_file_size(2500000000)
print(size)  # "2.3 GB"
```

---

## Uso Combinado

### Exemplo: Criar colaborador com email e relatório

```python
from app.models.employee import Employee
from app.utils.helpers import generate_temp_password
from app.utils.email import send_welcome_email
from app.utils.document_generator import generate_employee_report
from flask import current_app
from app.extensions.database import db

# Criar colaborador
temp_password = generate_temp_password()
employee = Employee(
    name="Maria Santos",
    email="maria@example.com",
    position="colaborador",
    restaurant_id=1
)
employee.set_password(temp_password)

db.session.add(employee)
db.session.commit()

# Enviar email de boas-vindas
send_welcome_email(
    employee_email=employee.email,
    employee_name=employee.name,
    temp_password=temp_password,
    app=current_app._get_current_object()
)

# Gerar relatório inicial
pdf_path = generate_employee_report(
    employee=employee,
    output_path=f"uploads/generated/employee_{employee.id}_report.pdf"
)

print(f"Colaborador criado: {employee.id}")
print(f"Email enviado para: {employee.email}")
print(f"Relatório gerado: {pdf_path}")
```

---

**Última atualização:** 18 de Dezembro de 2025
