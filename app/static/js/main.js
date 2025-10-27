// MAC Calendar - Main JavaScript

// API Configuration
const API_BASE_URL = '/api';
const STORAGE_KEYS = {
    AUTH_TOKEN: 'mac_auth_token',
    USER_DATA: 'mac_user_data',
    THEME: 'mac_theme',
    SETTINGS: 'mac_settings'
};

// Application State
class AppState {
    constructor() {
        this.user = null;
        this.theme = 'light';
        this.notifications = [];
        this.settings = {};
        this.init();
    }

    init() {
        this.loadFromStorage();
        this.setupEventListeners();
    }

    loadFromStorage() {
        try {
            const userData = localStorage.getItem(STORAGE_KEYS.USER_DATA);
            if (userData) {
                this.user = JSON.parse(userData);
            }

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
            console.error('Error loading from storage:', error);
        }
    }

    saveToStorage(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
        } catch (error) {
            console.error('Error saving to storage:', error);
        }
    }

    setupEventListeners() {
        // Theme toggle
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 't') {
                e.preventDefault();
                this.toggleTheme();
            }
        });

        // Auto-save forms
        document.addEventListener('input', this.debounce((e) => {
            if (e.target.hasAttribute('data-autosave')) {
                this.autoSaveForm(e.target.form);
            }
        }, 1000));
    }

    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.theme);
        localStorage.setItem(STORAGE_KEYS.THEME, this.theme);
    }

    applyTheme(theme) {
        document.body.setAttribute('data-theme', theme);
    }

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

    autoSaveForm(form) {
        if (!form) return;
        
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        localStorage.setItem(`form_${form.id || 'default'}`, JSON.stringify(data));
        
        Utils.showToast('Dados salvos automaticamente', 'success', 2000);
    }
}

// Utility Functions
class Utils {
    static formatDate(date, options = {}) {
        const defaultOptions = { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        };
        return new Date(date).toLocaleDateString('pt-BR', { ...defaultOptions, ...options });
    }

    static formatDateTime(date) {
        return new Date(date).toLocaleString('pt-BR');
    }

    static formatRelativeTime(date) {
        const now = new Date();
        const diff = now - new Date(date);
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (seconds < 60) return 'agora';
        if (minutes < 60) return `${minutes}m atrás`;
        if (hours < 24) return `${hours}h atrás`;
        if (days < 7) return `${days}d atrás`;
        return this.formatDate(date);
    }

    static showAlert(message, type = 'info', duration = 5000) {
        const alertContainer = document.getElementById('alert-container') || document.body;
        const alertId = 'alert-' + Date.now();
        
        const icons = {
            success: 'check-circle',
            error: 'exclamation-triangle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };

        const alertDiv = document.createElement('div');
        alertDiv.id = alertId;
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            <i class="fas fa-${icons[type] || 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.appendChild(alertDiv);
        
        // Auto dismiss
        if (duration > 0) {
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    bootstrap.Alert.getOrCreateInstance(alert).close();
                }
            }, duration);
        }

        return alertId;
    }

    static showToast(message, type = 'info', duration = 3000) {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }

        const toastId = 'toast-' + Date.now();
        const toastElement = document.createElement('div');
        toastElement.id = toastId;
        toastElement.className = `toast align-items-center text-bg-${type === 'error' ? 'danger' : type} border-0`;
        toastElement.setAttribute('role', 'alert');
        toastElement.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toastElement);
        
        const toast = new bootstrap.Toast(toastElement, { delay: duration });
        toast.show();

        // Clean up after toast is hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });

        return toastId;
    }

    static async makeRequest(url, options = {}) {
        const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` }),
                ...options.headers
            }
        };

        try {
            const response = await fetch(API_BASE_URL + url, {
                ...defaultOptions,
                ...options
            });
            
            if (response.status === 401) {
                this.handleUnauthorized();
                throw new Error('Unauthorized');
            }
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Request failed:', error);
            this.showAlert('Erro na requisição: ' + error.message, 'error');
            throw error;
        }
    }

    static handleUnauthorized() {
        localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
        localStorage.removeItem(STORAGE_KEYS.USER_DATA);
        window.location.href = '/auth/login';
    }

    static isAuthenticated() {
        return !!localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
    }

    static getCurrentUser() {
        const userData = localStorage.getItem(STORAGE_KEYS.USER_DATA);
        return userData ? JSON.parse(userData) : null;
    }

    static logout() {
        localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
        localStorage.removeItem(STORAGE_KEYS.USER_DATA);
        window.location.href = '/auth/login';
    }

    static validateForm(form) {
        const errors = [];
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                errors.push(`${field.getAttribute('data-label') || field.name} é obrigatório`);
                field.classList.add('is-invalid');
            } else {
                field.classList.remove('is-invalid');
            }
        });

        return errors;
    }

    static sanitizeInput(input) {
        const div = document.createElement('div');
        div.textContent = input;
        return div.innerHTML;
    }

    static copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Copiado para a área de transferência', 'success');
        }).catch(() => {
            this.showToast('Erro ao copiar texto', 'error');
        });
    }

    static downloadFile(data, filename, type = 'application/json') {
        const blob = new Blob([data], { type });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    // Format file size
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Format currency in Brazilian format
    static formatCurrency(amount) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(amount);
    }

    // Validate CPF
    static validateCPF(cpf) {
        cpf = cpf.replace(/[^\d]/g, '');
        
        if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) {
            return false;
        }
        
        let sum = 0;
        for (let i = 0; i < 9; i++) {
            sum += parseInt(cpf.charAt(i)) * (10 - i);
        }
        let checkDigit = 11 - (sum % 11);
        if (checkDigit === 10 || checkDigit === 11) checkDigit = 0;
        if (checkDigit !== parseInt(cpf.charAt(9))) return false;
        
        sum = 0;
        for (let i = 0; i < 10; i++) {
            sum += parseInt(cpf.charAt(i)) * (11 - i);
        }
        checkDigit = 11 - (sum % 11);
        if (checkDigit === 10 || checkDigit === 11) checkDigit = 0;
        
        return checkDigit === parseInt(cpf.charAt(10));
    }

    // Validate CNPJ
    static validateCNPJ(cnpj) {
        cnpj = cnpj.replace(/[^\d]/g, '');
        
        if (cnpj.length !== 14) return false;
        
        // Validate first check digit
        let sum = 0;
        let weight = 2;
        for (let i = 11; i >= 0; i--) {
            sum += parseInt(cnpj.charAt(i)) * weight;
            weight = weight === 9 ? 2 : weight + 1;
        }
        let checkDigit = sum % 11 < 2 ? 0 : 11 - (sum % 11);
        if (checkDigit !== parseInt(cnpj.charAt(12))) return false;
        
        // Validate second check digit
        sum = 0;
        weight = 2;
        for (let i = 12; i >= 0; i--) {
            sum += parseInt(cnpj.charAt(i)) * weight;
            weight = weight === 9 ? 2 : weight + 1;
        }
        checkDigit = sum % 11 < 2 ? 0 : 11 - (sum % 11);
        
        return checkDigit === parseInt(cnpj.charAt(13));
    }

    // Format phone number
    static formatPhone(phone) {
        phone = phone.replace(/[^\d]/g, '');
        if (phone.length === 11) {
            return phone.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
        } else if (phone.length === 10) {
            return phone.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
        }
        return phone;
    }

    // Format CPF
    static formatCPF(cpf) {
        cpf = cpf.replace(/[^\d]/g, '');
        return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    }

    // Format CNPJ
    static formatCNPJ(cnpj) {
        cnpj = cnpj.replace(/[^\d]/g, '');
        return cnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
    }

    // Debounce function for search inputs
    static debounce(func, wait) {
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

    // Generate random ID
    static generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
}

// API Classes
class AuthAPI {
    static async login(credentials) {
        const response = await Utils.makeRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify(credentials)
        });
        
        if (response.access_token) {
            localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, response.access_token);
            localStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(response.user));
        }
        
        return response;
    }

    static async register(userData) {
        return await Utils.makeRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    }

    static async refreshToken() {
        try {
            const response = await Utils.makeRequest('/auth/refresh', {
                method: 'POST'
            });
            
            if (response.access_token) {
                localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, response.access_token);
            }
            
            return response;
        } catch (error) {
            Utils.handleUnauthorized();
            throw error;
        }
    }
}

class CalendarAPI {
    static async getEvents(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return await Utils.makeRequest(`/calendar/events?${queryString}`);
    }

    static async createEvent(eventData) {
        return await Utils.makeRequest('/calendar/events', {
            method: 'POST',
            body: JSON.stringify(eventData)
        });
    }

    static async updateEvent(id, eventData) {
        return await Utils.makeRequest(`/calendar/events/${id}`, {
            method: 'PUT',
            body: JSON.stringify(eventData)
        });
    }

    static async deleteEvent(id) {
        return await Utils.makeRequest(`/calendar/events/${id}`, {
            method: 'DELETE'
        });
    }

    static async getEvent(id) {
        return await Utils.makeRequest(`/calendar/events/${id}`);
    }
}

class EmployeeAPI {
    static async getEmployees(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return await Utils.makeRequest(`/employees?${queryString}`);
    }

    static async createEmployee(employeeData) {
        return await Utils.makeRequest('/employees', {
            method: 'POST',
            body: JSON.stringify(employeeData)
        });
    }

    static async updateEmployee(id, employeeData) {
        return await Utils.makeRequest(`/employees/${id}`, {
            method: 'PUT',
            body: JSON.stringify(employeeData)
        });
    }

    static async deleteEmployee(id) {
        return await Utils.makeRequest(`/employees/${id}`, {
            method: 'DELETE'
        });
    }

    static async getEmployee(id) {
        return await Utils.makeRequest(`/employees/${id}`);
    }
}

class RestaurantAPI {
    static async getRestaurants(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return await Utils.makeRequest(`/restaurants?${queryString}`);
    }

    static async createRestaurant(restaurantData) {
        return await Utils.makeRequest('/restaurants', {
            method: 'POST',
            body: JSON.stringify(restaurantData)
        });
    }

    static async updateRestaurant(id, restaurantData) {
        return await Utils.makeRequest(`/restaurants/${id}`, {
            method: 'PUT',
            body: JSON.stringify(restaurantData)
        });
    }

    static async deleteRestaurant(id) {
        return await Utils.makeRequest(`/restaurants/${id}`, {
            method: 'DELETE'
        });
    }

    static async getRestaurant(id) {
        return await Utils.makeRequest(`/restaurants/${id}`);
    }
}

class DocumentAPI {
    static async generateDocument(type, data) {
        return await Utils.makeRequest('/documents/generate', {
            method: 'POST',
            body: JSON.stringify({ type, data })
        });
    }

    static async getDocuments(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return await Utils.makeRequest(`/documents?${queryString}`);
    }

    static async getDocument(id) {
        return await Utils.makeRequest(`/documents/${id}`);
    }

    static async deleteDocument(id) {
        return await Utils.makeRequest(`/documents/${id}`, {
            method: 'DELETE'
        });
    }
}

// Form Utilities
class FormHandler {
    constructor(formElement, options = {}) {
        this.form = formElement;
        this.options = {
            validateOnInput: true,
            showProgress: true,
            autoSave: false,
            ...options
        };
        this.init();
    }

    init() {
        if (this.options.validateOnInput) {
            this.setupValidation();
        }

        if (this.options.autoSave) {
            this.setupAutoSave();
        }

        this.form.addEventListener('submit', this.handleSubmit.bind(this));
    }

    setupValidation() {
        const inputs = this.form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => {
                if (input.classList.contains('is-invalid')) {
                    this.validateField(input);
                }
            });
        });
    }

    setupAutoSave() {
        const inputs = this.form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('input', Utils.debounce(() => {
                this.autoSave();
            }, 1000));
        });
    }

    validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let message = '';

        // Required validation
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            message = 'Este campo é obrigatório';
        }

        // Email validation
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                message = 'Email inválido';
            }
        }

        // Phone validation
        if (field.type === 'tel' && value) {
            const phoneRegex = /^\(\d{2}\)\s\d{4,5}-\d{4}$/;
            if (!phoneRegex.test(value)) {
                isValid = false;
                message = 'Telefone inválido (ex: (11) 99999-9999)';
            }
        }

        // Update field state
        field.classList.toggle('is-invalid', !isValid);
        field.classList.toggle('is-valid', isValid && value);

        // Show/hide feedback
        let feedback = field.parentNode.querySelector('.invalid-feedback');
        if (!feedback && !isValid) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentNode.appendChild(feedback);
        }

        if (feedback) {
            feedback.textContent = message;
            feedback.style.display = isValid ? 'none' : 'block';
        }

        return isValid;
    }

    validateForm() {
        const inputs = this.form.querySelectorAll('input, textarea, select');
        let isValid = true;

        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });

        return isValid;
    }

    async handleSubmit(event) {
        event.preventDefault();

        if (!this.validateForm()) {
            Utils.showAlert('Por favor, corrija os erros no formulário', 'error');
            return;
        }

        const submitButton = this.form.querySelector('[type="submit"]');
        const originalText = submitButton.textContent;

        try {
            // Show loading state
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processando...';

            // Get form data
            const formData = new FormData(this.form);
            const data = Object.fromEntries(formData);

            // Call submit handler if provided
            if (this.options.onSubmit) {
                await this.options.onSubmit(data);
            }

            Utils.showToast('Formulário enviado com sucesso!', 'success');

        } catch (error) {
            console.error('Form submission error:', error);
            Utils.showAlert('Erro ao enviar formulário: ' + error.message, 'error');
        } finally {
            // Restore button state
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }

    autoSave() {
        const formData = new FormData(this.form);
        const data = Object.fromEntries(formData);
        const key = `autosave_${this.form.id || 'form'}`;
        
        localStorage.setItem(key, JSON.stringify({
            data,
            timestamp: Date.now()
        }));

        Utils.showToast('Dados salvos automaticamente', 'info', 1500);
    }

    loadAutoSave() {
        const key = `autosave_${this.form.id || 'form'}`;
        const saved = localStorage.getItem(key);

        if (saved) {
            try {
                const { data, timestamp } = JSON.parse(saved);
                
                // Check if autosave is recent (within 24 hours)
                if (Date.now() - timestamp < 24 * 60 * 60 * 1000) {
                    Object.entries(data).forEach(([name, value]) => {
                        const field = this.form.querySelector(`[name="${name}"]`);
                        if (field) {
                            field.value = value;
                        }
                    });

                    Utils.showAlert('Dados anteriores restaurados automaticamente', 'info');
                }
            } catch (error) {
                console.error('Error loading autosave:', error);
            }
        }
    }
}

// Loading Manager
class LoadingManager {
    static show(message = 'Carregando...') {
        let loader = document.getElementById('global-loader');
        
        if (!loader) {
            loader = document.createElement('div');
            loader.id = 'global-loader';
            loader.className = 'loading-overlay';
            loader.innerHTML = `
                <div class="loading-content">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="loading-text mt-3">${message}</div>
                </div>
            `;
            document.body.appendChild(loader);
        }

        loader.querySelector('.loading-text').textContent = message;
        loader.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    static hide() {
        const loader = document.getElementById('global-loader');
        if (loader) {
            loader.style.display = 'none';
            document.body.style.overflow = '';
        }
    }
}

// Initialize Application
const appState = new AppState();

// Global initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('MAC Calendar System initialized');

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Setup global error handling
    window.addEventListener('error', function(event) {
        console.error('Global error:', event.error);
        Utils.showAlert('Ocorreu um erro inesperado. Tente novamente.', 'error');
    });

    // Setup AJAX error handling
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        Utils.showAlert('Erro de conexão. Verifique sua internet.', 'error');
    });

    // Auto-refresh token every 30 minutes if authenticated
    if (Utils.isAuthenticated()) {
        setInterval(async () => {
            try {
                await AuthAPI.refreshToken();
            } catch (error) {
                console.error('Token refresh failed:', error);
            }
        }, 30 * 60 * 1000);
    }
});

// Export for global access
window.MacCalendar = {
    Utils,
    AuthAPI,
    CalendarAPI,
    EmployeeAPI,
    RestaurantAPI,
    DocumentAPI,
    FormHandler,
    LoadingManager,
    appState
};