/**
 * MAC Calendar - Utilities
 * Funções utilitárias gerais e de documentos
 */

class Utils {
    // --- FUNÇÕES DE DOCUMENTOS (NOVAS) ---

    /**
     * Retorna o ícone FontAwesome baseado no nome do arquivo
     */
    static getFileIcon(filename) {
        if (!filename) return 'fa-file';
        const ext = filename.toLowerCase().split('.').pop();
        
        const map = {
            'fa-file-image': ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'],
            'fa-file-pdf': ['pdf'],
            'fa-file-word': ['doc', 'docx', 'txt'],
            'fa-file-excel': ['xls', 'xlsx', 'csv'],
            'fa-file-powerpoint': ['ppt', 'pptx'],
            'fa-file-archive': ['zip', 'rar', '7z']
        };

        for (const [icon, extensions] of Object.entries(map)) {
            if (extensions.includes(ext)) return icon;
        }
        return 'fa-file';
    }

    static getFileTypeLabel(filename) {
    if (!filename) return 'Arquivo';
    const ext = filename.toLowerCase().split('.').pop();
    
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'].includes(ext)) return 'Imagem';
    if (ext === 'pdf') return 'PDF';
    if (['doc', 'docx', 'txt'].includes(ext)) return 'Documento';
    if (['xls', 'xlsx', 'csv'].includes(ext)) return 'Planilha';
    if (['ppt', 'pptx'].includes(ext)) return 'Apresentação';
    if (['zip', 'rar', '7z'].includes(ext)) return 'Compactado';
    return 'Arquivo';
}

    /**
     * Retorna a cor contextual do Bootstrap baseada na extensão
     */
    static getFileColor(filename) {
        if (!filename) return 'secondary';
        const ext = filename.toLowerCase().split('.').pop();
        
        if (['jpg', 'jpeg', 'png', 'webp'].includes(ext)) return 'warning';
        if (ext === 'pdf') return 'danger';
        if (['doc', 'docx'].includes(ext)) return 'primary';
        if (['xls', 'xlsx', 'csv'].includes(ext)) return 'success';
        if (['ppt', 'pptx'].includes(ext)) return 'info';
        return 'secondary';
    }

    /**
     * Formata o tamanho do arquivo de bytes para humano
     */
    static formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // --- FUNÇÕES QUE VOCÊ JÁ TINHA (MANTIDAS) ---

    static formatDate(date, format = 'pt-BR') {
        if (!date) return '---';
        if (typeof date === 'string') date = new Date(date);
        
        if (format === 'pt-BR') {
            return date.toLocaleDateString('pt-BR', {
                year: 'numeric', month: '2-digit', day: '2-digit'
            });
        }
        return date.toISOString().split('T')[0];
    }

    static formatTime(date, format = 'HH:mm') {
        if (!date) return '--:--';
        if (typeof date === 'string') date = new Date(date);
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return format === 'HH:mm:ss' ? `${hours}:${minutes}:${String(date.getSeconds()).padStart(2, '0')}` : `${hours}:${minutes}`;
    }

    static formatDateTime(date) {
        return `${this.formatDate(date)} ${this.formatTime(date)}`;
    }

    static truncate(str, length = 100) {
        if (!str) return '';
        return str.length <= length ? str : str.substring(0, length) + '...';
    }

    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('Copiado para a área de transferência', 'success');
            return true;
        } catch (error) { return false; }
    }

    static showAlert(message, type = 'info', duration = 5000) {
        const alertContainer = document.getElementById('alert-container') || document.body;
        const alertId = 'alert-' + Date.now();
        const icons = { success: 'check-circle', error: 'exclamation-triangle', warning: 'exclamation-triangle', info: 'info-circle' };

        const alertDiv = document.createElement('div');
        alertDiv.id = alertId;
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alertDiv.innerHTML = `<i class="fas fa-${icons[type] || 'info-circle'} me-2"></i>${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;

        alertContainer.prepend(alertDiv);
        if (duration > 0) setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) bootstrap.Alert.getOrCreateInstance(alert).close();
        }, duration);
        return alertId;
    }

    static showToast(message, type = 'info', duration = 3000) {
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }

        const toastElement = document.createElement('div');
        toastElement.className = `toast align-items-center text-bg-${type === 'error' ? 'danger' : type} border-0`;
        toastElement.setAttribute('role', 'alert');
        toastElement.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>`;

        toastContainer.appendChild(toastElement);
        const toast = new bootstrap.Toast(toastElement, { delay: duration });
        toast.show();
        toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
    }


    


}

window.Utils = Utils;