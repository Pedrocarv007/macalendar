/**
 * MAC Calendar - App Init
 * Inicializa a aplicação
 */

class App {
    static instance = null;

    constructor() {
        this.initialized = false;
    }

    static getInstance() {
        if (!this.instance) {
            this.instance = new App();
        }
        return this.instance;
    }

    /**
     * Inicializar aplicação
     */
    async init() {
        if (this.initialized) return;

        try {
            console.log('🚀 Inicializando MAC Calendar...');

            // Inicializar state
            appState.init();
            console.log('✓ Estado inicializado');

            // Configurar event listeners
            this.setupGlobalHandlers();
            console.log('✓ Event listeners configurados');

            // Verificar autenticação
            await this.checkAuth();
            console.log('✓ Autenticação verificada');

            // Inicializar módulos específicos da página
            this.initPageModules();
            console.log('✓ Módulos da página inicializados');

            this.initialized = true;
            console.log('✅ MAC Calendar inicializado com sucesso!');

        } catch (error) {
            console.error('❌ Erro ao inicializar:', error);
        }
    }

    /**
     * Verificar autenticação
     */
    async checkAuth() {
        try {
            // Tentar /auth/user primeiro (sessão)
            const user = await api.get('/auth/user');
            if (user && user.id) {
                appState.setUser(user);
            }
        } catch (error) {
            // Usuário não autenticado
            console.log('Usuário não autenticado');
        }
    }

    /**
     * Setup global handlers
     */
    setupGlobalHandlers() {
        // Fechar modais com ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const modals = DOM.$$('.modal.show');
                modals.forEach(modal => {
                    const backdrop = modal.previousElementSibling;
                    if (backdrop && backdrop.classList.contains('modal-backdrop')) {
                        backdrop.remove();
                    }
                    modal.classList.remove('show');
                });
            }
        });

        // Logout
        DOM.on('.btn-logout', 'click', (e) => {
            e.preventDefault();
            this.logout();
        });

        // Toggle sidebar
        DOM.on('.btn-toggle-sidebar', 'click', (e) => {
            e.preventDefault();
            DOM.toggleClass('body', 'sidebar-collapsed');
        });
    }

    /**
     * Inicializar módulos específicos da página
     */
    initPageModules() {
        const path = window.location.pathname;

        if (path.includes('/employees')) {
            if (typeof EmployeesModule !== 'undefined') {
                EmployeesModule.init();
            }
        } else if (path.includes('/restaurants')) {
            if (typeof RestaurantsModule !== 'undefined') {
                RestaurantsModule.init();
            }
        } else if (path.includes('/documents')) {
            if (typeof DocumentsModule !== 'undefined') {
                DocumentsModule.init();
            }
        } else if (path.includes('/calendar')) {
            if (typeof CalendarModule !== 'undefined') {
                CalendarModule.init();
            }
        } else if (path.includes('/dashboard')) {
            if (typeof DashboardModule !== 'undefined') {
                DashboardModule.init();
            }
        }
    }

    /**
     * Fazer logout
     */
    async logout() {
        try {
            await api.get('/auth/logout');
            appState.clear();
            const loginPath = window.APP_PREFIX ? `${window.APP_PREFIX}/auth/login` : '/auth/login';
            window.location.href = loginPath;
        } catch (error) {
            console.error('Erro ao fazer logout:', error);
        }
    }

    /**
     * Mostrar notificação
     */
    notify(message, type = 'info') {
        const notification = appState.notify(message, type);
        
        // Criar elemento de notificação
        const element = DOM.createElement('div', {
            class: `alert alert-${type} alert-dismissible fade show`,
            role: 'alert'
        }, [
            message,
            DOM.createElement('button', {
                type: 'button',
                class: 'btn-close',
                'data-bs-dismiss': 'alert',
                'aria-label': 'Close'
            })
        ]);

        const container = DOM.$('.notifications-container') || this.createNotificationContainer();
        container.appendChild(element);

        // Auto-remover após duração
        if (notification.duration > 0) {
            setTimeout(() => {
                element.remove();
            }, notification.duration);
        }
    }

    /**
     * Criar container de notificações
     */
    createNotificationContainer() {
        const container = DOM.createElement('div', {
            class: 'notifications-container position-fixed top-0 end-0 p-3',
            style: {
                zIndex: 9999,
                maxWidth: '400px'
            }
        });
        document.body.appendChild(container);
        return container;
    }
}

/**
 * Inicializar quando DOM estiver pronto
 */
document.addEventListener('DOMContentLoaded', () => {
    App.getInstance().init();
});

// Expor globalmente
window.App = App.getInstance();
