# Sistema de Fotos para Colaboradores e Restaurantes

## Visão Geral

O sistema MAC Calendar agora suporta upload de fotos para colaboradores e restaurantes.

## Funcionalidades

### Colaboradores

- **Upload de Foto**: Ao criar ou editar um colaborador, é possível fazer upload de uma foto
- **Preview**: Visualização em tempo real da foto antes de salvar
- **Placeholder**: Imagem padrão é exibida para colaboradores sem foto
- **Exibição**: As fotos aparecem na lista e na visualização em grid de colaboradores
- **Remover**: Possibilidade de remover a foto de um colaborador

### Restaurantes

- **Upload de Foto**: Ao criar ou editar um restaurante, é possível fazer upload de uma foto
- **Preview**: Visualização em tempo real da foto antes de salvar
- **Placeholder**: Imagem padrão é exibida para restaurantes sem foto
- **Exibição**: As fotos aparecem como capa dos cards de restaurantes na visualização em grid
- **Remover**: Possibilidade de remover a foto de um restaurante

## Formatos Suportados

- PNG
- JPG / JPEG
- GIF

Máximo de 5MB por arquivo

## Endpoints da API

### Colaboradores

```
POST /api/employees/<employee_id>/upload-photo
- Faz upload de foto para um colaborador
- Requer: arquivo (multipart/form-data)
- Retorna: photo_filename, photo_url

DELETE /api/employees/<employee_id>/photo
- Remove a foto de um colaborador
- Retorna: mensagem de sucesso
```

### Restaurantes

```
POST /api/restaurants/<restaurant_id>/upload-photo
- Faz upload de foto para um restaurante
- Requer: arquivo (multipart/form-data)
- Retorna: photo_filename, photo_url

DELETE /api/restaurants/<restaurant_id>/photo
- Remove a foto de um restaurante
- Retorna: mensagem de sucesso
```

## Armazenamento

### Estrutura de Diretórios

```
app/static/
├── uploads/
│   ├── employees/
│   │   └── employee_<id>_<timestamp>.jpg
│   ├── restaurants/
│   │   └── restaurant_<id>_<timestamp>.jpg
│   └── images/
│       └── placeholder-user.jpg (imagem padrão)
```

### Limpeza

Fotos antigas são automaticamente removidas quando:
- Uma nova foto é enviada para o mesmo usuário/restaurante
- A foto é deletada via API ou interface

## Banco de Dados

### Campos Adicionados

**Tabela employees**:
- `photo_filename` (VARCHAR(255), nullable)

**Tabela restaurants**:
- `photo_filename` (VARCHAR(255), nullable)

### Exemplos de Dados

```json
{
  "id": 1,
  "name": "João Silva",
  "email": "joao@example.com",
  "photo_filename": "employee_1_1701875432.45.jpg",
  ...
}
```

## Processamento de Imagens

As imagens são:
1. Convertidas para RGB (remove transparência)
2. Redimensionadas:
   - Colaboradores: 400x400px máximo
   - Restaurantes: 600x400px máximo
3. Comprimidas com qualidade 85%
4. Salvas como JPEG otimizado

## Permissões

Para fazer upload ou remover fotos:
- **Admin/RH**: Pode gerenciar fotos de qualquer colaborador/restaurante
- **Manager**: Pode gerenciar fotos apenas do seu próprio restaurante
- **Employee**: Não tem permissão

## Exemplos de Uso

### Upload via JavaScript

```javascript
async function uploadPhoto(employeeId, file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`/api/employees/${employeeId}/upload-photo`, {
        method: 'POST',
        body: formData
    });
    
    const result = await response.json();
    console.log(result.photo_url);
}
```

### Remover Foto

```javascript
async function removePhoto(employeeId) {
    const response = await fetch(`/api/employees/${employeeId}/photo`, {
        method: 'DELETE'
    });
    
    const result = await response.json();
    console.log(result.message);
}
```

## Troubleshooting

### Foto não aparece após upload

1. Verifique se a pasta `app/static/uploads/` existe
2. Verifique as permissões da pasta (deve ser gravável)
3. Verifique o console do navegador para mensagens de erro
4. Verifique os logs da aplicação Flask

### Erro ao processar imagem

- O formato do arquivo pode não ser suportado (use PNG, JPG ou GIF)
- A imagem pode estar corrompida
- O arquivo pode ser maior que 5MB

### Placeholder não aparece

- Verifique se `app/static/images/placeholder-user.jpg` existe
- Verifique se o caminho da imagem está correto no HTML
