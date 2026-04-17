# Rate Limiting e Cache - OpenAI

## Visão Geral

Implementação de rate limiting e cache para proteger o sistema contra uso abusivo de APIs OpenAI e reduzir custos.

## Limites Atuais

| Endpoint | Limite | Janela |
|----------|--------|--------|
| `/api/ai/posts` | 100 requisições | 1 hora |
| `/api/calendar/generate/mystery-tuesdays` | 10 requisições | 1 dia |
| `/api/calendar/generate/mystery-answers` | 10 requisições | 1 dia |
| `/api/documents/generate` | 50 requisições | 1 hora |

## Cache

- **TTL (Time To Live):** 1 hora
- **Estratégia:** Memória (em produção, considerar Redis)
- **Validação:** Parâmetros de entrada (topic, tone, length, language)

Exemplo: Se 2 utilizadores pedem o mesmo post com os mesmos parâmetros, o segundo obterá do cache sem custo de API.

## Uso

### Integração em Endpoints

```python
from app.utils.rate_limiter import check_rate_limit, with_cache

@app.route('/api/generate', methods=['POST'])
@api_login_required
@check_rate_limit      # Verifica limite
@with_cache           # Cacheia resposta
def generate():
    return jsonify({'result': '...'})
```

### Resposta ao Exceder Limite

```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Muitas requisições. Tente novamente mais tarde.",
  "retry_after": 3600,
  "remaining": 0
}
```

## Personalização

Para modificar limites, editar `app/utils/rate_limiter.py`:

```python
self.limits = {
    '/api/seu/endpoint': {
        'requests': 50,    # número de requisições
        'window': 3600     # janela em segundos
    }
}
```

## ⚠️ Limitações

1. **Em Memória:** Limpa ao reiniciar a aplicação
2. **Sem Persistência:** Não funciona com múltiplas instâncias
3. **Sem Redis:** Considerar Redis para produção escalável

## Próximos Passos

1. [ ] Implementar com Redis para escalabilidade
2. [ ] Adicionar logs de uso de API
3. [ ] Dashboard de monitoramento de custos
4. [ ] Alertas quando aproximar de limites
