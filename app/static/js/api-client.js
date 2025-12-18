/**
 * MAC Calendar - API Client
 * Módulo para comunicação com a API do servidor
 */

const detectAppPrefix = () => {
    const basePath = window.location.pathname;
    const [ , maybePrefix ] = basePath.split('/');
    if (!maybePrefix) return '';

    const candidate = `/${maybePrefix}`;
    return candidate.toLowerCase() === '/mac' ? candidate : '';
};

const APP_PREFIX = detectAppPrefix();
const API_BASE_URL = `${window.location.origin}${APP_PREFIX}/api`;

window.APP_PREFIX = APP_PREFIX;
window.API_BASE_URL = API_BASE_URL;

class APIClient {
    constructor(baseURL = API_BASE_URL) {
        this.baseURL = baseURL;
        console.log(`📡 API Client inicializado`);
        console.log(`   📍 window.location.pathname: ${window.location.pathname}`);
        console.log(`   🔑 APP_PREFIX detectado: "${APP_PREFIX}"`);
        console.log(`   📡 baseURL: ${this.baseURL}`);
    }

    /**
     * Fazer requisição GET
     */
    async get(endpoint, options = {}) {
        return this.request('GET', endpoint, null, options);
    }

    /**
     * Fazer requisição POST
     */
    async post(endpoint, data, options = {}) {
        return this.request('POST', endpoint, data, options);
    }

    /**
     * Fazer requisição PUT
     */
    async put(endpoint, data, options = {}) {
        return this.request('PUT', endpoint, data, options);
    }

    /**
     * Fazer requisição DELETE
     */
    async delete(endpoint, options = {}) {
        return this.request('DELETE', endpoint, null, options);
    }

    /**
     * Requisição genérica
     */
    async request(method, endpoint, data = null, options = {}) {
        let url = `${this.baseURL}${endpoint}`;
        
        console.log(`🔵 REQUEST: ${method} ${url}`);
        console.log(`   baseURL: ${this.baseURL}`);
        console.log(`   endpoint: ${endpoint}`);
        
        const isFormData = data instanceof FormData;
        
        const config = {
            method,
            headers: isFormData ? {} : {
                'Content-Type': 'application/json',
                ...options.headers
            },
            credentials: 'include',  // ✅ Enviar cookies/session
            ...options
        };

        if (data) {
            if (isFormData) {
                // FormData será enviado como multipart/form-data
                // Não definir Content-Type, o navegador faz automaticamente
                config.body = data;
            } else {
                config.body = JSON.stringify(data);
            }
        }

        try {
            console.log(`➡️  ${method} ${url}`);
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                if (typeof Utils !== 'undefined' && typeof Utils.handleUnauthorized === 'function') {
                    Utils.handleUnauthorized();
                }
                throw new APIError(response.status, 'Unauthorized', response);
            }

            if (!response.ok) {
                const text = await response.text();
                let error = {};
                try {
                    error = JSON.parse(text);
                } catch (e) {
                    error = { error: text || `HTTP ${response.status}` };
                }

                console.error(`❌ API Error ${response.status}:`, {
                    url,
                    status: response.status,
                    statusText: response.statusText,
                    error
                });

                throw new APIError(response.status, error.error || error.message || 'Request failed', response);
            }

            // Se for DELETE ou 204 No Content, retornar vazio
            if (method === 'DELETE' || response.status === 204) {
                console.log(`✓ ${method} ${url} - 204 No Content`);
                return { success: true };
            }

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                console.warn(`⚠️  Resposta não é JSON: ${contentType}`);
                console.warn(`   Response text: ${await response.text()}`);
                throw new APIError(response.status, 'Response is not JSON', response);
            }

            const result = await response.json();
            console.log(`✓ ${method} ${url} - 200 OK`);
            return result;
        } catch (error) {
            console.error(`❌ API Error [${method} ${url}]:`, error);
            if (typeof Utils !== 'undefined' && typeof Utils.showAlert === 'function') {
                Utils.showAlert('Erro na requisição: ' + (error.message || 'Falha desconhecida'), 'error');
            }
            throw error;
        }
    }
}

/**
 * Classe para erros de API
 */
class APIError extends Error {
    constructor(status, message, response) {
        super(message);
        this.status = status;
        this.response = response;
        this.name = 'APIError';
    }
}

// Instância global
const api = new APIClient();
window.api = api;
