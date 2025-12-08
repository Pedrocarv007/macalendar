/**
 * MAC Calendar - Utilities
 * Funções utilitárias gerais
 */

class Utils {
    /**
     * Formatar data
     */
    static formatDate(date, format = 'pt-BR') {
        if (typeof date === 'string') {
            date = new Date(date);
        }
        
        if (format === 'pt-BR') {
            return date.toLocaleDateString('pt-BR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
        } else if (format === 'ISO') {
            return date.toISOString().split('T')[0];
        }
        
        return date.toString();
    }

    /**
     * Formatar hora
     */
    static formatTime(date, format = 'HH:mm') {
        if (typeof date === 'string') {
            date = new Date(date);
        }

        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');

        if (format === 'HH:mm') {
            return `${hours}:${minutes}`;
        } else if (format === 'HH:mm:ss') {
            return `${hours}:${minutes}:${seconds}`;
        }

        return `${hours}:${minutes}`;
    }

    /**
     * Formatar data e hora
     */
    static formatDateTime(date) {
        return `${this.formatDate(date, 'pt-BR')} ${this.formatTime(date, 'HH:mm')}`;
    }

    /**
     * Validar email
     */
    static isValidEmail(email) {
        const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return pattern.test(email);
    }

    /**
     * Validar telefone
     */
    static isValidPhone(phone) {
        const clean = phone.replace(/\D/g, '');
        return clean.length >= 10 && clean.length <= 11;
    }

    /**
     * Capitalizar string
     */
    static capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    }

    /**
     * Truncar string
     */
    static truncate(str, length = 100) {
        if (!str) return '';
        if (str.length <= length) return str;
        return str.substring(0, length) + '...';
    }

    /**
     * Copiar para clipboard
     */
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (error) {
            console.error('Erro ao copiar:', error);
            return false;
        }
    }

    /**
     * Gerar UUID
     */
    static generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * Deep clone de objeto
     */
    static deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (obj instanceof Object) {
            const cloned = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    cloned[key] = this.deepClone(obj[key]);
                }
            }
            return cloned;
        }
    }

    /**
     * Merging objetos
     */
    static mergeObjects(target, source) {
        for (const key in source) {
            if (source.hasOwnProperty(key)) {
                if (typeof source[key] === 'object' && source[key] !== null) {
                    target[key] = this.mergeObjects(target[key] || {}, source[key]);
                } else {
                    target[key] = source[key];
                }
            }
        }
        return target;
    }

    /**
     * Esperar (sleep)
     */
    static sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Fazer Utils disponível globalmente
window.Utils = Utils;
