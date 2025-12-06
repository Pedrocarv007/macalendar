# Sistema de Edição de Perfil - MAC Calendar

## Visão Geral

O sistema MAC Calendar agora possui uma página de perfil completamente funcional onde os usuários podem:
- Editar suas informações pessoais
- Upload de foto de perfil
- Alterar sua senha
- Visualizar estatísticas pessoais (anos de trabalho, dias até aniversário)

## Funcionalidades

### Edição de Informações Pessoais

Os usuários podem editar os seguintes campos:
- **Nome Completo**: Seu nome completo
- **Telefone**: Número de contato
- **Endereço**: Endereço residencial
- **Observações**: Notas pessoais

Campos **não editáveis**:
- Email (definido durante o cadastro)
- Cargo (position)
- Departamento (department)
- Função no Sistema (role)
- Data de Nascimento (birth_date)
- Data de Contratação (hire_date)

### Upload de Foto de Perfil

- Clique no avatar ou na câmera para fazer upload de uma foto
- Formatos suportados: PNG, JPG, JPEG, GIF
- Imagem é automaticamente redimensionada para 400x400px
- Foto antiga é removida ao fazer upload de uma nova
- Possibilidade de remover a foto

### Alteração de Senha

- Verificação de senha atual (obrigatória)
- Nova senha deve ter no mínimo 6 caracteres
- Confirmação de nova senha

### Estatísticas Pessoais

Exibidas no card do perfil:
- **Anos de Trabalho**: Calculado a partir da data de contratação
- **Dias para Aniversário**: Dias até o próximo aniversário

## Endpoints da API

### GET /api/profile/me
Obter dados do perfil do usuário autenticado

**Response (200)**:
```json
{
  "id": 1,
  "name": "João Silva",
  "email": "joao@example.com",
  "phone": "(351) 912 345 678",
  "position": "Gerente",
  "department": "Administração",
  "role": "admin",
  "birth_date": "1990-05-15",
  "hire_date": "2022-01-10",
  "address": "Rua Principal, 123",
  "notes": "Observações pessoais",
  "photo_filename": "employee_1_1701875432.45.jpg",
  "work_years": 2,
  "days_until_birthday": 125,
  "is_birthday_today": false
}
```

### PUT /api/profile/me
Atualizar dados do perfil (edição permitida)

**Body**:
```json
{
  "name": "João Silva",
  "phone": "(351) 912 345 678",
  "address": "Rua Principal, 123",
  "notes": "Observações pessoais"
}
```

**Response (200)**:
```json
{
  "message": "Perfil atualizado com sucesso",
  "user": { /* dados do usuário */ }
}
```

### POST /api/profile/me/photo
Fazer upload de foto do perfil

**Body**: multipart/form-data
- file: arquivo de imagem

**Response (200)**:
```json
{
  "message": "Foto enviada com sucesso",
  "photo_filename": "employee_1_1701875432.45.jpg",
  "photo_url": "/static/uploads/employees/employee_1_1701875432.45.jpg"
}
```

### DELETE /api/profile/me/photo
Remover foto do perfil

**Response (200)**:
```json
{
  "message": "Foto deletada com sucesso"
}
```

### POST /api/profile/me/password
Alterar senha do usuário

**Body**:
```json
{
  "current_password": "senha_atual",
  "new_password": "nova_senha"
}
```

**Response (200)**:
```json
{
  "message": "Senha alterada com sucesso"
}
```

## Interface de Usuário

### Modo de Leitura
- Todos os campos são exibidos como somente leitura
- Botão "Editar" disponível

### Modo de Edição
- Campos editáveis ficam habilitados (exceto email)
- Avatar fica interativo (clique para fazer upload de foto)
- Botões "Salvar" e "Cancelar" aparecem

### Fluxo de Uso

1. **Acesse o Perfil**
   - Clique em "Meu Perfil" no menu

2. **Edite Informações**
   - Clique em "Editar"
   - Preencha os campos desejados
   - Clique em "Salvar"

3. **Adicione Foto**
   - Em modo de edição, clique na foto
   - Selecione uma imagem do seu computador
   - A foto é automaticamente carregada

4. **Remova Foto**
   - Em modo de edição, clique em "Remover Foto"
   - Confirme a remoção

5. **Altere Senha**
   - Preencha os campos de senha
   - Clique em "Alterar Senha"
   - Digite sua senha atual e a nova senha
   - Clique em "Alterar Senha"

## Segurança

- Todos os endpoints requerem autenticação (`@api_login_required`)
- Emails não podem ser editados (apenas para criação de conta)
- Senhas são hash com werkzeug.security
- Fotos antigas são removidas do servidor automaticamente
- Validação de tipos de arquivo (PNG, JPG, GIF)
- Compressão de imagens (qualidade 85%)

## Dados Calculados

### work_years
Calcula anos de trabalho baseado na `hire_date`:
```
years = hoje.year - hire_date.year - (
  (hoje.month, hoje.day) < (hire_date.month, hire_date.day)
)
```

### days_until_birthday
Calcula dias até o próximo aniversário:
```
next_birthday = birth_date.replace(year=hoje.year)
if next_birthday < hoje:
  next_birthday = birth_date.replace(year=hoje.year + 1)
days = (next_birthday - hoje).days
```

### is_birthday_today
Verifica se é aniversário:
```
(hoje.month, hoje.day) == (birth_date.month, birth_date.day)
```

## Exemplos de Uso

### JavaScript - Obter Perfil
```javascript
const response = await fetch('/api/profile/me');
const profile = await response.json();
console.log(profile.name); // João Silva
```

### JavaScript - Atualizar Perfil
```javascript
const response = await fetch('/api/profile/me', {
  method: 'PUT',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    name: 'João Silva Costa',
    phone: '(351) 912 345 999',
    address: 'Rua Nova, 456',
    notes: 'Novas observações'
  })
});
const result = await response.json();
console.log(result.message); // Perfil atualizado com sucesso
```

### JavaScript - Alterar Senha
```javascript
const response = await fetch('/api/profile/me/password', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    current_password: 'senha_atual',
    new_password: 'nova_senha_123'
  })
});
const result = await response.json();
console.log(result.message); // Senha alterada com sucesso
```

## Troubleshooting

### "Erro ao carregar perfil"
- Verifique se você está autenticado
- Verifique se o token JWT está válido
- Verifique os logs da aplicação

### Foto não aparece após upload
- Verifique se a pasta `app/static/uploads/employees/` existe
- Verifique as permissões da pasta (deve ser gravável)
- Verifique o console do navegador para mensagens de erro

### Erro ao alterar senha
- Verifique se a senha atual está correta
- Nova senha deve ter no mínimo 6 caracteres
- Verifique se as senhas coincidem

### Campos não editáveis
- Email não pode ser editado (use criar nova conta)
- Cargo, Departamento, Role só podem ser editados por administradores
- Use a página de colaboradores para editar esses campos
