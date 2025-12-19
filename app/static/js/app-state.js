/**
 * MAC Calendar - App State
 * Gerencia estado global da aplicação
 */

const STORAGE_KEYS = {
    AUTH_TOKEN: 'mac_auth_token',
    USER_DATA: 'mac_user_data',
    THEME: 'mac_theme',
    SETTINGS: 'mac_settings'
};

class AppState {
    constructor() {
        this.user = null;
        this.theme = 'light';
        this.notifications = [];
        this.settings = {};
        this.cache = new Map();
    }

    /**
     * Inicializar estado
     */
    init() {
        this.loadFromStorage();
        this.setupEventListeners();
    }

    /**
     * Carregar dados do localStorage
     */
    loadFromStorage() {
        try {
            const theme = localStorage.getItem(STORAGE_KEYS.THEME);
            if (theme) {
                this.theme = theme;
                this.applyTheme(theme);
            }

            const settings = localStorage.getItem(STORAGE_KEYS.SETTINGS);
            if (settings) {
                this.settings = JSON.parse(settings);
            }
        } catch (error) {
            // Silenciar erros de storage
        }
    }

    /**
     * Salvar dados no localStorage
     */
    saveToStorage(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
        } catch (error) {
            // Silenciar erros de storage
        }
    }

    /**
     * Setup de event listeners
     */
    setupEventListeners() {
        // Alternar tema com Ctrl+T
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 't') {
                e.preventDefault();
                this.toggleTheme();
            }
        });

        // Auto-save de formulários
        document.addEventListener('input', this.debounce((e) => {
            if (e.target.hasAttribute('data-autosave')) {
                this.autoSaveForm(e.target.form);
            }
        }, 1000));
    }

    /**
     * Alternar tema
     */
    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.theme);
        this.saveToStorage(STORAGE_KEYS.THEME, this.theme);
    }

    /**
     * Aplicar tema
     */
    applyTheme(theme) {
        document.body.setAttribute('data-theme', theme);
    }

    /**
     * Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Auto-save de formulário
     */
    autoSaveForm(form) {
        if (!form) return;
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        this.saveToStorage(`form_${form.id}`, data);
    }

    /**
     * Definir usuário
     */
    setUser(user) {
        this.user = user;
        this.saveToStorage(STORAGE_KEYS.USER_DATA, user);
    }

    /**
     * Limpar estado (logout)
     */
    clear() {
        this.user = null;
        this.notifications = [];
        this.cache.clear();
        localStorage.removeItem(STORAGE_KEYS.USER_DATA);
        localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
    }

    /**
     * Adicionar notificação
     */
    notify(message, type = 'info', duration = 3000) {
        const notification = {
            id: Date.now(),
            message,
            type,
            duration
        };
        this.notifications.push(notification);
        
        if (duration > 0) {
            setTimeout(() => {
                this.notifications = this.notifications.filter(n => n.id !== notification.id);
            }, duration);
        }

        return notification;
    }

    /**
     * Cache de dados
     */
    getCache(key) {
        return this.cache.get(key);
    }

    setCache(key, value, ttl = 300000) {
        this.cache.set(key, value);
        if (ttl > 0) {
            setTimeout(() => this.cache.delete(key), ttl);
        }
    }
}

// Instância global
const appState = new AppState();
