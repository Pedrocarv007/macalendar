/**
 * MAC Calendar - Dashboard Module
 * Módulo para gerenciar o dashboard principal
 */

const DashboardModule = {
    // Data do módulo
    stats: {},
    events: [],
    activities: [],
    
    /**
     * Inicializar o módulo
     */
    init() {
        console.log('📊 Inicializando Dashboard Module...');
        this.loadDashboardData();
        
        // Configurar listeners
        document.querySelectorAll('[data-action="refresh-dashboard"]').forEach(btn => {
            btn.addEventListener('click', () => this.loadDashboardData());
        });
        
        document.querySelectorAll('[data-action="export-data"]').forEach(btn => {
            btn.addEventListener('click', () => this.exportData());
        });
    },
    
    /**
     * Carregar dados do dashboard
     */
    async loadDashboardData() {
        try {
            console.log('📥 Carregando dados do dashboard...');
            
            // Load stats via API
            this.stats = await api.get('/dashboard/stats');
            this.updateStatsUI();
            
            // Load recent events
            this.events = await api.get('/dashboard/events/recent');
            this.renderRecentEvents();
            
            // Load activity feed
            this.activities = await api.get('/dashboard/activities');
            this.renderActivityFeed();
            
            console.log('✓ Dashboard carregado com sucesso');
            appState.notify('Dashboard atualizado', 'success');
            
        } catch (error) {
            console.error('❌ Erro ao carregar dashboard:', error);
            appState.notify('Erro ao carregar dashboard: ' + error.message, 'error');
        }
    },
    
    /**
     * Atualizar UI de estatísticas
     */
    updateStatsUI() {
        const elements = {
            'totalEmployees': this.stats.employees || 0,
            'todayEvents': this.stats.todayEvents || 0,
            'totalRestaurants': this.stats.restaurants || 0,
            'totalDocuments': this.stats.documents || 0
        };
        
        for (const [elementId, value] of Object.entries(elements)) {
            const el = document.getElementById(elementId);
            if (el) {
                el.textContent = value;
            }
        }
    },
    
    /**
     * Renderizar eventos recentes
     */
    renderRecentEvents() {
        const container = document.getElementById('recentEvents');
        
        if (!container) return;
        
        if (!this.events || this.events.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-4">
                    <i class="fas fa-calendar-times text-muted" style="font-size: 3rem;"></i>
                    <p class="text-muted mt-2">Nenhum evento próximo</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.events.map(event => `
            <div class="col-md-6">
                <div class="event-card">
                    <div class="d-flex align-items-center">
                        <div class="event-date">
                            <div class="day">${new Date(event.date).getDate()}</div>
                            <div class="month">${new Date(event.date).toLocaleDateString('pt-BR', {month: 'short'})}</div>
                        </div>
                        <div class="ms-3 flex-grow-1">
                            <h6 class="mb-1">${event.title}</h6>
                            <p class="text-muted mb-0">${event.description || 'Sem descrição'}</p>
                            <small class="text-muted">
                                <i class="fas fa-clock me-1"></i>
                                ${new Date(event.date).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    },
    
    /**
     * Renderizar feed de atividades
     */
    renderActivityFeed() {
        const container = document.getElementById('activityFeed');
        
        if (!container) return;
        
        if (!this.activities || this.activities.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-bell-slash text-muted" style="font-size: 3rem;"></i>
                    <p class="text-muted mt-2">Nenhuma atividade recente</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon ${activity.type}">
                    <i class="fas fa-${activity.icon}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${activity.title}</div>
                    <div class="activity-desc">${activity.description}</div>
                    <div class="activity-time">${this.formatRelativeTime(activity.timestamp)}</div>
                </div>
            </div>
        `).join('');
    },
    
    /**
     * Formatar tempo relativo (ex: "2 horas atrás")
     */
    formatRelativeTime(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diff = now - time;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'Agora';
        if (minutes < 60) return `${minutes}m atrás`;
        if (hours < 24) return `${hours}h atrás`;
        return `${days}d atrás`;
    },
    
    /**
     * Exportar dados
     */
    async exportData() {
        try {
            appState.notify('Iniciando exportação de dados...', 'info');
            // TODO: Implementar exportação (CSV, PDF, etc)
            console.log('Exportação não implementada ainda');
        } catch (error) {
            console.error('Erro ao exportar:', error);
            appState.notify('Erro ao exportar dados', 'error');
        }
    }
};
