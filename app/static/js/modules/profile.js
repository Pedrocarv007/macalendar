/**
 * MAC Calendar - Profile Module
 * Módulo para gerenciar perfil do usuário
 */

const ProfileModule = {
    user: null,
    
    /**
     * Inicializar o módulo
     */
    async init() {
        try {
            // Obter usuário atual via sessão
            this.user = await api.get('/auth/user');
            this.setupHandlers();
            this.displayProfile();
        } catch (error) {
            // Silenciar erro
        }
    },
    
    /**
     * Setup event handlers
     */
    setupHandlers() {
        // Handlers dos botões podem ser configurados aqui
    },
    
    /**
     * Carregar perfil
     */
    async loadProfile() {
        try {
            this.user = await api.get('/auth/me');
            this.displayProfile();
        } catch (error) {
            appState.notify('Erro ao carregar perfil', 'error');
        }
    },
    
    /**
     * Exibir perfil
     */
    displayProfile() {
        // Será implementado conforme necessário
    },
    
    /**
     * Atualizar perfil
     */
    async updateProfile(profileData) {
        try {
            this.user = await api.put('/auth/profile', profileData);
            appState.setUser(this.user);
            appState.notify('Perfil atualizado com sucesso', 'success');
            this.displayProfile();
        } catch (error) {
            appState.notify('Erro ao atualizar perfil', 'error');
        }
    },
    
    /**
     * Atualizar foto
     */
    async updatePhoto(file) {
        try {
            const formData = new FormData();
            formData.append('photo', file);
            const response = await fetch(api.baseURL + '/auth/profile/photo', {
                method: 'PUT',
                body: formData
            });
            if (response.ok) {
                appState.notify('Foto atualizada com sucesso', 'success');
                this.loadProfile();
            }
        } catch (error) {
            appState.notify('Erro ao atualizar foto', 'error');
        }
    },
    
    /**
     * Mudar senha
     */
    async changePassword(currentPassword, newPassword) {
        try {
            await api.post('/auth/change-password', {
                current_password: currentPassword,
                new_password: newPassword
            });
            appState.notify('Senha alterada com sucesso', 'success');
        } catch (error) {
            appState.notify('Erro ao mudar senha', 'error');
        }
    }
};
