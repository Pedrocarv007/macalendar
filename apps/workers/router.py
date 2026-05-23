class SSORouter:
    """
    Encaminha Worker e SSORestaurant para a base de dados 'sso'.
    Impede migrações nessas tabelas (geridas pelo SSO Portal).
    """
    _SSO_MODELS = {'worker', 'ssorestaurant', 'ssouser'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'workers' and model._meta.model_name in self._SSO_MODELS:
            return 'sso'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'workers' and model._meta.model_name in self._SSO_MODELS:
            return 'sso'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'sso':
            # Nunca migrar nada no SSO DB — é gerido externamente
            return False
        if app_label == 'workers' and model_name in self._SSO_MODELS:
            # Não migrar modelos SSO na DB local (managed=False já trata disso)
            return False
        return None
