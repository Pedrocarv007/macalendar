import os
import sys
from pathlib import Path

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Load environment without importing the app first
from dotenv import load_dotenv
load_dotenv(BASE_DIR / '.env')

from app import create_app
from app.utils.email import send_email

html_content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
	<meta charset="UTF-8">
	<title>Teste SMTP | MAC Calendar</title>
	<style>
		body {
			margin: 0;
			padding: 0;
			background: #f5f7fb;
			color: #243447;
			font-family: 'Segoe UI', Arial, sans-serif;
		}
		.container {
			max-width: 640px;
			margin: 0 auto;
			padding: 32px 24px;
		}
		.card {
			background: #ffffff;
			border: 1px solid #e5e9f2;
			border-radius: 12px;
			box-shadow: 0 8px 20px rgba(18, 38, 63, 0.08);
			padding: 32px;
		}
		.brand {
			text-align: center;
			margin-bottom: 24px;
		}
		.brand h1 {
			margin: 8px 0 0 0;
			font-size: 24px;
			color: #0f6ddf;
		}
		.badge {
			display: inline-block;
			background: #e8f1ff;
			color: #0f6ddf;
			padding: 6px 12px;
			border-radius: 999px;
			font-weight: 600;
			font-size: 12px;
			letter-spacing: 0.5px;
		}
		h2 {
			color: #141c2c;
			margin: 0 0 8px 0;
			font-size: 20px;
		}
		p {
			margin: 0 0 12px 0;
			line-height: 1.6;
		}
		.list {
			margin: 16px 0;
			padding-left: 18px;
		}
		.list li {
			margin-bottom: 10px;
		}
		.panel {
			background: #f8fafc;
			border: 1px solid #e5e9f2;
			border-radius: 10px;
			padding: 14px 16px;
			margin: 16px 0;
			font-family: 'SFMono-Regular', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
			font-size: 13px;
			color: #1f2937;
		}
		.cta {
			text-align: center;
			margin: 24px 0 12px 0;
		}
		.cta a {
			display: inline-block;
			background: #0f6ddf;
			color: #ffffff;
			padding: 12px 20px;
			border-radius: 8px;
			text-decoration: none;
			font-weight: 600;
		}
		.footer {
			text-align: center;
			color: #6b778c;
			font-size: 12px;
			margin-top: 16px;
			line-height: 1.4;
		}
	</style>
</head>
<body>
	<div class="container">
		<div class="card">
			<div class="brand">
				<span class="badge">MAC Calendar</span>
				<h1>Teste de Entrega</h1>
			</div>
			<h2>Seu SMTP está funcionando.</h2>
			<p>Recebemos este e-mail de teste para confirmar a entrega pelo servidor configurado. Se você está lendo esta mensagem, sua configuração SMTP está ativa e pronta para uso.</p>
			<div class="panel">
				<strong>Checklist rápido:</strong><br>
				• Remetente configurado: verifique o nome e o endereço exibidos.<br>
				• Conteúdo renderizado: títulos, parágrafos e botões devem aparecer bem formatados.<br>
				• Links e imagens: confira se seu provedor não bloqueia conteúdos externos.
			</div>
			<h2>Próximos passos sugeridos</h2>
			<ul class="list">
				<li>Envie um teste para outro domínio (ex.: Gmail/Outlook) para validar reputação.</li>
				<li>Adicione o remetente aos contatos para evitar filtro de spam.</li>
				<li>Habilite SPF/DKIM/DMARC no seu domínio para máxima entregabilidade.</li>
			</ul>
			<div class="cta">
				<a href="https://" target="_blank" rel="noopener">Acessar MAC Calendar</a>
			</div>
			<p>Qualquer dúvida, responda este e-mail e nossa equipe ajudará você a finalizar a configuração.</p>
			<div class="footer">
				MAC Calendar · Thecarv Sistemas<br>
				Mensagem automática de validação SMTP
			</div>
		</div>
	</div>
</body>
</html>"""


def main():
	print(f"ENV MAIL_USERNAME={os.environ.get('MAIL_USERNAME')!r}")
	print(f"ENV MAIL_PASSWORD set?={'yes' if os.environ.get('MAIL_PASSWORD') else 'no'}")
	print(f"ENV MAIL_DEFAULT_SENDER={os.environ.get('MAIL_DEFAULT_SENDER')!r}")

	config_name = os.environ.get('APP_CONFIG') or 'development'
	app = create_app(config_name)
	with app.app_context():
		cfg = app.config
		server = cfg.get('MAIL_SERVER')
		port = cfg.get('MAIL_PORT')
		use_tls = cfg.get('MAIL_USE_TLS')
		username = cfg.get('MAIL_USERNAME')
		sender = cfg.get('MAIL_DEFAULT_SENDER') or username
		password = cfg.get('MAIL_PASSWORD')

		print(f"CFG MAIL_USERNAME={username!r}")
		print(f"CFG MAIL_DEFAULT_SENDER={sender!r}")
		if password and ' ' in str(password):
			print('Aviso: sua MAIL_PASSWORD contém espaços. Para Gmail App Password, use os 16 caracteres sem espaços.')

		if not username:
			print('MAIL_USERNAME não configurado. Configure seu email remetente.')
			return 1
		if not password:
			print('MAIL_PASSWORD não configurado. Cole sua App Password do Gmail (16 dígitos, sem espaços).')
			return 1
		print(f"Enviando e-mail de teste via {server}:{port} TLS={use_tls} como {sender} -> {username}")
		try:
			send_email(
				to=username,
				subject='MAC Calendar - Teste SMTP',
				html=html_content ,
				text='Teste SMTP OK.'
			)
			print('E-mail de teste enviado com sucesso!')
		except Exception as e:
			print(f'Falha ao enviar e-mail de teste: {e}')
			return 1
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
