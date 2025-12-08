/**
 * MAC Calendar - API Client
 * Módulo para comunicação com a API do servidor
 */

// Detectar se está rodando com /mac prefix - SEMPRE usar /mac por padrão
let APP_PREFIX = '/mac';

// Construir a baseURL dinamicamente baseada no domínio atual
// Se estiver via www.thecarv.com, usar o mesmo domínio
// Se estiver via localhost, usar o mesmo
let API_BASE_URL;

if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    // Local development
    API_BASE_URL = `http://${window.location.hostname}:6005${APP_PREFIX}/api`;
} else {
    // Production (www.thecarv.com ou qualquer outro domínio)
    API_BASE_URL = `${window.location.protocol}//${window.location.hostname}${APP_PREFIX}/api`;
}

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
        
        const config = {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            credentials: 'include',  // ✅ Enviar cookies/session
            ...options
        };

        if (data) {
            config.body = JSON.stringify(data);
        }

        try {
            console.log(`➡️  ${method} ${url}`);
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const text = await response.text();
                let error = {};
                try {
                    error = JSON.parse(text);
                } catch (e) {
                    error = { error: text || `HTTP ${response.status}` };
                }
                
                // Log detalhado de erro
                console.error(`❌ API Error ${response.status}:`, {
                    url: url,
                    status: response.status,
                    statusText: response.statusText,
                    error: error
                });
                
                throw new APIError(response.status, error.error || 'Request failed', response);
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
