# Guia Rápido - Sistema de Fotos e Perfil

## O que foi adicionado

### 1. Fotos para Colaboradores e Restaurantes
- Upload de imagens (PNG, JPG, GIF)
- Exibição em formulários, listas e cards
- Remoção de fotos
- Redimensionamento automático

### 2. Página de Perfil Completa
- Edição de informações pessoais
- Upload de foto de perfil
- Alteração de senha
- Visualização de estatísticas

## Como Usar

### Adicionar Foto a um Colaborador

1. Vá para **Colaboradores**
2. Clique em editar um colaborador
3. Clique na foto no topo do formulário
4. Selecione uma imagem do seu computador
5. A foto é carregada automaticamente
6. Clique em "Salvar" para confirmar

### Adicionar Foto a um Restaurante

1. Vá para **Restaurantes**
2. Clique em editar um restaurante
3. Clique na foto no topo do formulário
4. Selecione uma imagem do seu computador
5. A foto é carregada automaticamente
6. Clique em "Salvar" para confirmar

### Editar Seu Perfil

1. Clique em **Meu Perfil** (canto superior direito)
2. Clique em **Editar**
3. Atualize os campos desejados:
   - Nome
   - Telefone
   - Endereço
   - Observações
4. Para adicionar/alterar foto:
   - Clique na foto
   - Selecione uma imagem
5. Clique em **Salvar**

### Alterar Sua Senha

1. Vá para **Meu Perfil**
2. Role até **Alterar Senha**
3. Preencha os campos:
   - Senha atual (obrigatória)
   - Nova senha (mínimo 6 caracteres)
   - Confirmar senha
4. Clique em **Alterar Senha**

## Características Técnicas

### Armazenamento
- Fotos são salvas em `app/static/uploads/`
- Estrutura: `employees/`, `restaurants/`
- Formato: JPEG otimizado
- Tamanho máximo: 5MB

### Processamento
- Redimensionamento automático
- Compressão de qualidade 85%
- Conversão para RGB (sem transparência)
- Remoção de fotos antigas

### Banco de Dados
- Campo `photo_filename` em `employees`
- Campo `photo_filename` em `restaurants`
- Campo `photo_filename` em `users` (não aplicável)

## Endpoints da API

### Colaboradores
```
POST   /api/employees/<id>/upload-photo
DELETE /api/employees/<id>/photo
```

### Restaurantes
```
POST   /api/restaurants/<id>/upload-photo
DELETE /api/restaurants/<id>/photo
```

### Perfil
```
GET    /api/profile/me
PUT    /api/profile/me
POST   /api/profile/me/photo
DELETE /api/profile/me/photo
POST   /api/profile/me/password
```

## Permissões

- **Admin/RH**: Pode gerenciar fotos de qualquer pessoa
- **Manager**: Pode gerenciar fotos apenas do seu restaurante
- **Employee**: Pode editar apenas seu próprio perfil

## Formatos Aceitos

- ✓ PNG
- ✓ JPG / JPEG
- ✓ GIF
- ✗ BMP
- ✗ WebP
- ✗ TIFF

## Resolução de Problemas

### A foto não aparece
- Verifique se o arquivo foi carregado corretamente
- Verifique se a pasta `uploads/` tem permissões de escrita
- Limpe o cache do navegador (Ctrl+Shift+Delete)

### Erro ao fazer upload
- Arquivo muito grande? (máximo 5MB)
- Formato não suportado?
- Disco cheio?

### A senha não muda
- Senha atual está incorreta?
- Nova senha é muito curta? (mínimo 6 caracteres)
- As senhas coincidem?

### Perfil não carrega
- Você está autenticado?
- Token JWT está válido?
- Verifique a conexão com a internet

## Próximas Melhorias Sugeridas

- [ ] Crop de imagem antes de fazer upload
- [ ] Galeria de fotos (múltiplas imagens)
- [ ] Filtro de fotos por data
- [ ] Backup automático de fotos
- [ ] Sincronização com redes sociais
- [ ] QR code no perfil
- [ ] Histórico de alterações de perfil

## Documentação Completa

Para mais detalhes, consulte:
- `PHOTOS_SYSTEM.md` - Sistema de fotos
- `PROFILE_SYSTEM.md` - Sistema de perfil
