import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Dict, Iterable, Optional, Union
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


def _resolve_mail_settings(cfg, profile: Optional[str]) -> Dict[str, Union[str, int, bool, None]]:
	"""Resolve SMTP settings, optionally from a named profile."""
	# Profiles come from settings.MAIL_PROFILES or env MAIL_PROFILES (JSON string)
	profiles = cfg.get('MAIL_PROFILES') or {}
	selected = profiles.get(profile) if profile else None

	# Allow a "default" profile name to be used implicitly
	if not selected and not profile and 'default' in profiles:
		selected = profiles.get('default')

	server = None
	port = None
	use_tls = None
	username = None
	password = None
	default_sender = None

	if isinstance(selected, dict):
		server = selected.get('server')
		port = selected.get('port')
		use_tls = selected.get('use_tls')
		username = selected.get('username')
		password = selected.get('password')
		default_sender = selected.get('default_sender')

	server = server or cfg.get('MAIL_SERVER') or os.environ.get('MAIL_SERVER') or 'smtp.zoho.eue'
	port = int(port or cfg.get('MAIL_PORT') or os.environ.get('MAIL_PORT') or 587)
	use_tls_raw = use_tls if use_tls is not None else (cfg.get('MAIL_USE_TLS') or os.environ.get('MAIL_USE_TLS', 'true'))
	use_tls = str(use_tls_raw).lower() in ['true', 'on', '1']
	username = username or cfg.get('MAIL_USERNAME') or os.environ.get('MAIL_USERNAME') or "thecarv@thecarv.com"
	password = password or cfg.get('MAIL_PASSWORD') or os.environ.get('MAIL_PASSWORD') or "5d77iUBJiviV"
	default_sender = default_sender or cfg.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_DEFAULT_SENDER')

	return {
		'server': server,
		'port': port,
		'use_tls': use_tls,
		'username': username,
		'password': password,
		'default_sender': default_sender,
	}


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
	mail_profile: Optional[str] = None,
) -> None:
	"""Send an email using SMTP settings.

	You can configure multiple profiles via MAIL_PROFILES (JSON) in env or app config.
	Pass mail_profile="profile_name" to pick one; otherwise uses the base config or
	a profile named "default" when present.
	"""
	cfg = current_app.config
	resolved = _resolve_mail_settings(cfg, mail_profile)

	server = resolved['server']
	port = resolved['port']
	use_tls = resolved['use_tls']
	username = resolved['username']
	password = resolved['password']

	# Always send using the authenticated address to avoid 530 errors.
	sender_cfg = resolved['default_sender']
	sender_cfg_clean = str(sender_cfg).strip().strip('\"\'') if sender_cfg else None
	display_name = None
	if sender_cfg_clean:
		m = re.match(r"\s*([^<]+?)\s*<([^>]+)>\s*", sender_cfg_clean)
		if m:
			display_name = m.group(1).strip().strip('\"\'')
		else:
			if '@' not in sender_cfg_clean:
				display_name = sender_cfg_clean.strip('\"\'')

	sender_address = username
	sender_display = display_name.strip('\"\'') if display_name else None
	sender = f"{sender_display} <{sender_address}>" if sender_display else sender_address
	envelope_from = sender_address

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
			smtp.send_message(msg, from_addr=envelope_from, to_addrs=all_recipients)
	else:
		with smtplib.SMTP(server, port) as smtp:
			smtp.ehlo()
			if username and password:
				smtp.login(username, password)
			smtp.send_message(msg, from_addr=envelope_from, to_addrs=all_recipients)


def send_email_async(**kwargs) -> Thread:
	"""Send email in a background thread. Returns the Thread instance."""
	def _runner(app_obj, params):
		with app_obj.app_context():
			send_email(**params)

	app = current_app._get_current_object()
	t = Thread(target=_runner, args=(app, kwargs), daemon=True)
	t.start()
	return t

