"""
Tradução de perfis do TheCarV SSO para os perfis internos do MC.

O SSO (CustomUser.Role em Thecarv_django) usa nomes próprios — ex.: 'manager',
'sub_manager', 'shift_manager' — que diferem dos Employee.ROLE_CHOICES do MC
MC — ex.: 'gerente_loja', 'sub_gerente', 'gerente_turno'. Sem esta
tradução, um gerente vindo do SSO ficava guardado como 'manager' e falhava
silenciosamente as verificações de permissão (que procuram 'gerente_loja').

Perfis do SSO sem equivalente no MC (operacionais / sem acesso a este
sistema, ex.: 'rp', 'treinador', 'administrativa') e quaisquer valores
desconhecidos são despromovidos para 'employee' — menor privilégio.
"""

# Valor do perfil SSO -> valor Employee.role do MC
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
