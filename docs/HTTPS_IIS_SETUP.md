# HTTPS & Segurança em IIS

## ✅ Implementado no Código

A aplicação Flask agora inclui headers de segurança automáticos:

### Headers Adicionados

| Header | Valor | Proteção |
|--------|-------|----------|
| `Strict-Transport-Security` | `max-age=31536000` | Força HTTPS (1 ano) |
| `X-Content-Type-Options` | `nosniff` | Previne MIME sniffing |
| `X-Frame-Options` | `DENY` | Protege contra clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Ativa filtro XSS |
| `Content-Security-Policy` | ... | Mitiga XSS e injection |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Privacidade |
| `Permissions-Policy` | Bloqueia câmara, microfone, etc | Privacy |

## 🔧 Configuração HTTPS em IIS

### 1. **Gerar/Obter Certificado SSL**

**Opção A: Let's Encrypt (Grátis)**
```powershell
# Instalar Certbot para Windows
choco install certbot

# Gerar certificado
certbot certonly --standalone -d seu-dominio.pt

# Certificado fica em: C:\Certbot\live\seu-dominio.pt\
```

**Opção B: Certificado Auto-assinado (Teste)**
```powershell
$cert = New-SelfSignedCertificate -DnsName "localhost" `
  -FriendlyName "MAC Calendar" -NotAfter (Get-Date).AddYears(1)
```

**Opção C: Certificado Pago**
- GoDaddy, DigiCert, GlobalSign, etc.

### 2. **Importar Certificado em IIS**

1. Abrir **IIS Manager**
2. Clicar em seu servidor
3. **Server Certificates** → **Import**
4. Selecionar arquivo `.pfx` ou `.pem` + password

### 3. **Configurar HTTPS no Site**

1. Em IIS Manager → Site → **Bindings**
2. Clicar **Add**
3. Configurar:
   ```
   Type: https
   IP: *
   Port: 443
   Hostname: seu-dominio.pt
   SSL Certificate: [Selecionar certificado importado]
   ```
4. Clicar **OK**

### 4. **Redirecionar HTTP → HTTPS**

**Opção A: Via IIS URL Rewrite**
1. **Add Rule** → **Blank Rule**
2. Nome: "HTTP to HTTPS Redirect"
3. Pattern: `.*`
4. Rewrite URL: `https://{HTTP_HOST}/{R:0}`
5. Append query string: ✓
6. Stop processing: ✓

**Opção B: Via código Flask** (já implementado)
- Verificar se `X-Forwarded-Proto: https`

### 5. **web.config para IIS**

Deve incluir:
```xml
<rewrite>
  <rules>
    <rule name="HTTPS Redirect" stopProcessing="true">
      <match url="(.*)" />
      <conditions>
        <add input="{HTTPS}" pattern="^OFF$" />
      </conditions>
      <action type="Redirect" url="https://{HTTP_HOST}{REQUEST_URI}" redirectType="Permanent" />
    </rule>
  </rules>
</rewrite>
```

### 6. **Validar HTTPS**

```powershell
# Testar certificado
$cert = Get-ChildItem -Path Cert:\LocalMachine\My | where {$_.Subject -like "*seu-dominio*"}
$cert | Format-List *

# Testar acesso HTTPS
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}
$response = Invoke-WebRequest -Uri "https://seu-dominio.pt/api" -UseBasicParsing
$response.Headers
```

---

## 🔒 Verificação de Segurança

### Testar Headers

```powershell
# PowerShell
$headers = (Invoke-WebRequest -Uri "https://seu-dominio.pt").Headers
$headers | Where-Object { $_.Name -like "Strict-Transport*" }
```

### Tester Online
- https://securityheaders.com
- https://www.ssllabs.com/ssltest/

---

## ⚠️ Ambiente vs Produção

### Desenvolvimento (DEBUG=true)
- HSTS desativado
- CSP mais relaxado
- Testes locais sem HTTPS

### Produção (DEBUG=false)
- ✅ HSTS ativado (força HTTPS)
- ✅ CSP restritivo
- ✅ X-Frame-Options: DENY
- ✅ Certificado SSL válido

---

## Troubleshooting

### Erro 403 em HTTPS
- Verificar se porta 443 está aberta no firewall
- Verificar certificado não está expirado
- Verificar binding em IIS

### Headers não aparecem
- Reiniciar IIS: `iisreset`
- Limpar cache do browser: Ctrl+Shift+Delete

### Certificado expirado
- Renovar com Certbot: `certbot renew`
- Ou gerar novo certificado
- Atualizar binding em IIS

---

## ✅ Checklist

- [ ] Certificado SSL obtido e válido
- [ ] Certificado importado em IIS
- [ ] HTTPS binding criado (porta 443)
- [ ] HTTP redirecionado para HTTPS
- [ ] web.config tem rule de redirect
- [ ] `FLASK_DEBUG=false` em `.env`
- [ ] Headers de segurança confirmados via securityheaders.com
- [ ] Certificado testado com ssllabs.com
