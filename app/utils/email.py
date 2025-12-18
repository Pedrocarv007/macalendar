import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Iterable, Optional, Union
from flask import current_app
from threading import Thread
import mimetypes


def _guess_mime_type(path: str):
	mime_type, _ = mimetypes.guess_type(path)
	if not mime_type:
		return 'application', 'octet-stream'
	maintype, subtype = mime_type.split('/', 1)
	return maintype, subtype


def _ensure_list(value: Optional[Union[str, Iterable[str]]]) -> list[str]:
	if not value:
		return []
	if isinstance(value, str):
		return [value]
	return list(value)


def _build_message(
	*,
	subject: str,
	sender: str,
	to: Iterable[str],
	html: Optional[str] = None,
	text: Optional[str] = None,
	cc: Optional[Iterable[str]] = None,
	bcc: Optional[Iterable[str]] = None,
	reply_to: Optional[str] = None,
	attachments: Optional[Iterable[str]] = None,
) -> EmailMessage:
	msg = EmailMessage()
	msg['Subject'] = subject
	msg['From'] = sender
	msg['To'] = ', '.join(_ensure_list(to))
	if cc:
		msg['Cc'] = ', '.join(_ensure_list(cc))
	if reply_to:
		msg['Reply-To'] = reply_to

	# Body
	if html and text:
		msg.set_content(text)
		msg.add_alternative(html, subtype='html')
	elif html:
		# Derive a basic text fallback
		msg.set_content((html or '').replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n'))
		msg.add_alternative(html, subtype='html')
	else:
		msg.set_content(text or '')

	# Attachments
	for path in _ensure_list(attachments):
		if not path:
			continue
		try:
			maintype, subtype = _guess_mime_type(path)
			with open(path, 'rb') as f:
				data = f.read()
			filename = os.path.basename(path)
			msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)
		except Exception as e:
			# Do not fail the whole email on a single attachment error
			current_app.logger.exception(f"Falha ao anexar arquivo '{path}': {e}")

	# BCC is not set as header; handled at send time
	msg.__dict__.setdefault('_bcc', _ensure_list(bcc))
	return msg


def send_email(
	*,
	to: Union[str, Iterable[str]],
	subject: str,
	html: Optional[str] = None,
	text: Optional[str] = None,
	cc: Optional[Union[str, Iterable[str]]] = None,
	bcc: Optional[Union[str, Iterable[str]]] = None,
	reply_to: Optional[str] = None,
	attachments: Optional[Union[str, Iterable[str]]] = None,
) -> None:
	"""Send an email using SMTP settings from Flask config or environment.

	Reads from Flask config first, then falls back to environment variables.
	"""
	# Try Flask config first, then fall back to environment
	cfg = current_app.config
	server = cfg.get('MAIL_SERVER') or os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
	port = int(cfg.get('MAIL_PORT') or os.environ.get('MAIL_PORT') or 587)
	use_tls = str(cfg.get('MAIL_USE_TLS') or os.environ.get('MAIL_USE_TLS', 'true')).lower() in ['true', 'on', '1']
	username = cfg.get('MAIL_USERNAME') or os.environ.get('MAIL_USERNAME')
	password = cfg.get('MAIL_PASSWORD') or os.environ.get('MAIL_PASSWORD')
	
	# Always send using the authenticated Gmail address to avoid 530 errors.
	# Preserve friendly display name from MAIL_DEFAULT_SENDER if provided.
	sender_cfg = cfg.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_DEFAULT_SENDER')
	display_name = None
	if sender_cfg:
		# Extract display name if in format: Name <email>
		m = re.match(r"\s*([^<]+?)\s*<([^>]+)>\s*", str(sender_cfg))
		if m:
			display_name = m.group(1).strip()
		else:
			# If sender_cfg is a plain email or plain text, use as display name only if not an email
			if '@' not in str(sender_cfg):
				display_name = str(sender_cfg).strip()
	
	# Construct final sender as "Name <username>" or just username
	sender = f"{display_name} <{username}>" if display_name else username

	if not server:
		raise RuntimeError('MAIL_SERVER não configurado')
	if not username:
		raise RuntimeError('MAIL_USERNAME não configurado')

	msg = _build_message(
		subject=subject,
		sender=sender,
		to=_ensure_list(to),
		html=html,
		text=text,
		cc=_ensure_list(cc),
		bcc=_ensure_list(bcc),
		reply_to=reply_to,
		attachments=_ensure_list(attachments),
	)

	all_recipients = _ensure_list(to) + _ensure_list(cc) + msg.__dict__.get('_bcc', [])

	context = ssl.create_default_context()
	if use_tls:
		with smtplib.SMTP(server, port) as smtp:
			smtp.ehlo()
			smtp.starttls(context=context)
			smtp.ehlo()
			if username and password:
				smtp.login(username, password)
			smtp.send_message(msg, from_addr=sender, to_addrs=all_recipients)
	else:
		with smtplib.SMTP(server, port) as smtp:
			smtp.ehlo()
			if username and password:
				smtp.login(username, password)
			smtp.send_message(msg, from_addr=sender, to_addrs=all_recipients)


def send_email_async(**kwargs) -> Thread:
	"""Send email in a background thread. Returns the Thread instance."""
	def _runner(app_obj, params):
		with app_obj.app_context():
			send_email(**params)

	app = current_app._get_current_object()
	t = Thread(target=_runner, args=(app, kwargs), daemon=True)
	t.start()
	return t

