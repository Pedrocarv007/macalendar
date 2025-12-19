# Debugar Função de Deletar Evento

## Passos para testar:

### 1. **Abrir Console do Navegador**
   - Pressiona `F12` no navegador
   - Vai na aba "Console"

### 2. **Abrir Terminal do Servidor**
   - Onde o servidor Flask está rodando (deve ver logs do terminal)

### 3. **Tentar Deletar um Evento**
   - No calendário, clica num evento para abrir os detalhes
   - Clica no botão "Deletar"
   - Confirma no SweetAlert2

### 4. **Verificar Logs do Console (Navegador)**
   Deve ver:
   ```
   🗑️ deleteEvent chamado com ID: [número]
   🗑️ Resultado do Swal: true
   🗑️ Enviando DELETE para /calendar/events/[número]
   🗑️ Resposta do DELETE: {message: "Evento deletado com sucesso"}
   🗑️ Recarregando eventos...
   🗑️ Eventos recarregados
   ```

### 5. **Verificar Logs do Servidor (Terminal)**
   Deve ver:
   ```
   🗑️ [DELETE] Recebido pedido para deletar evento [número]
   🗑️ [DELETE] User: [id], Role: [role], Restaurant: [restaurant_id]
   🗑️ [DELETE] Evento encontrado: [título]
   🗑️ [DELETE] Deletando evento [número]...
   🗑️ [DELETE] Evento [número] deletado com sucesso
   ```

### 6. **Reportar o que Vê**
   Envia-me:
   - ✅ O que aparece no console do navegador
   - ✅ O que aparece no terminal do servidor
   - ✅ Se o evento desaparece ou fica no calendário

## Possíveis Problemas:

### ❌ Se não vir logs no navegador:
- A função `deleteEvent()` não está sendo chamada
- Problema: Pode estar a chamar `deleteEventFromDetails()` mas essa função não está a chamar corretamente

### ❌ Se vir logs no navegador mas não no servidor:
- A requisição não está a chegar ao servidor
- Problema: API prefix está errado
- Solução: Verifica a URL que está a ser enviada (vê no Network do Chrome F12 → Network tab)

### ❌ Se vir "Permissão negada" no servidor:
- `event.restaurant_id != user_restaurant_id` ou `event.created_by != current_user_id`
- Verifica que o utilizador é o criador do evento

### ❌ Se vir logs de sucesso mas evento não desaparece:
- A página não está a recarregar corretamente
- Problema: `loadEvents()` pode estar a falhar silenciosamente
