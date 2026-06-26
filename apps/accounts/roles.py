"""
Tradução de roles vindos do TheCarV SSO para os roles internos do Mac Calendar.

O SSO (CustomUser.Role em Thecarv_django) usa nomes próprios — ex.: 'manager',
'sub_manager', 'shift_manager' — que diferem dos Employee.ROLE_CHOICES do Mac
Calendar — ex.: 'gerente_loja', 'sub_gerente', 'gerente_turno'. Sem esta
tradução, um gerente vindo do SSO ficava guardado como 'manager' e falhava
silenciosamente as verificações de permissão (que procuram 'gerente_loja').

Roles do SSO sem equivalente no Mac Calendar (operacionais / sem acesso a este
sistema, ex.: 'rp', 'treinador', 'administrativa') e quaisquer valores
desconhecidos são despromovidos para 'employee' — menor privilégio.
"""

# SSO role value  ->  Mac Calendar Employee.role value
SSO_ROLE_MAP = {
    'admin':          'admin',
    'rh':             'rh',
    'marketing':      'marketing',
    'employee':       'employee',
    'manager':        'gerente_loja',
    'sub_manager':    'sub_gerente',
    'shift_manager':  'gerente_turno',
    # Sem equivalente / sem acesso ao sistema — menor privilégio:
    'rp':             'employee',
    'treinador':      'employee',
    'administrativa': 'employee',
}

DEFAULT_ROLE = 'employee'


def map_sso_role(raw):
    """Converte um role do SSO no role interno equivalente.

    Devolve sempre um role válido de Employee.ROLE_CHOICES; valores vazios,
    desconhecidos ou sem equivalente caem em 'employee'.
    """
    if not raw:
        return DEFAULT_ROLE
    return SSO_ROLE_MAP.get(str(raw).strip().lower(), DEFAULT_ROLE)
