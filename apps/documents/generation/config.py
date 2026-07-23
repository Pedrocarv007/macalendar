"""Catálogo central dos modelos gráficos disponíveis."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateDefinition:
    key: str
    label: str
    description: str
    filename: str
    accent: str
    photo_offset: int


TEMPLATES = {
    "birthday": TemplateDefinition(
        key="birthday",
        label="Aniversário",
        description="Cartão de aniversário do colaborador.",
        filename="aniversario.png",
        accent="#FFBC0D",
        photo_offset=-50,
    ),
    "welcome": TemplateDefinition(
        key="welcome",
        label="Boas-vindas",
        description="Cartão de acolhimento para novas pessoas.",
        filename="bem_vindo.png",
        accent="#2D2D2D",
        photo_offset=-50,
    ),
    "employee_month": TemplateDefinition(
        key="employee_month",
        label="Funcionário do Mês",
        description="Destaque mensal de um membro da equipa.",
        filename="funcionario_mes.png",
        accent="#FFBC0D",
        photo_offset=50,
    ),
}


RESTAURANT_TEMPLATE_OVERRIDES = {
    "paco de arcos": {"birthday": "aniversarios.png"},
}


def get_template_definition(key):
    return TEMPLATES.get(str(key or "").strip())


def public_template_catalog():
    return [
        {
            "key": item.key,
            "label": item.label,
            "description": item.description,
            "accent": item.accent,
            "filename": item.filename,
        }
        for item in TEMPLATES.values()
    ]
