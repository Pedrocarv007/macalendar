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
            const currentUser = appState?.user || {};
            const userRole = (currentUser.role || '').toLowerCase();
            const userRestaurantId = currentUser.restaurant_id;
            
            // Se não for admin, filtrar por restaurante
            const queryParams = {};
            if (!['admin', 'rh'].includes(userRole) && userRestaurantId) {
                queryParams.restaurant_id = userRestaurantId;
            }
            
            // Load stats via API
            const statsUrl = '/dashboard/stats' + (Object.keys(queryParams).length ? '?' + new URLSearchParams(queryParams).toString() : '');
            this.stats = await api.get(statsUrl);
            this.updateStatsUI();
            
            // Load recent events
            const eventsUrl = '/dashboard/events/recent' + (Object.keys(queryParams).length ? '?' + new URLSearchParams(queryParams).toString() : '');
            this.events = await api.get(eventsUrl);
            this.renderRecentEvents();
            
            // Load activity feed
            const activitiesUrl = '/dashboard/activities' + (Object.keys(queryParams).length ? '?' + new URLSearchParams(queryParams).toString() : '');
            this.activities = await api.get(activitiesUrl);
            this.renderActivityFeed();
            
            appState.notify('Dashboard atualizado', 'success');
            
        } catch (error) {
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

        const events = Array.isArray(this.events) ? this.events : [];
        if (!events.length) {
            container.innerHTML = `
                <div class="col-12">
                    <div class="card glass-card">
                        <div class="card-body text-center py-4">
                            <i class="fas fa-calendar-alt text-muted" style="font-size: 2.5rem;"></i>
                            <p class="text-muted mt-2 mb-0">Sem eventos recentes para este restaurante</p>
                        </div>
                    </div>
                </div>`;
            return;
        }

        container.innerHTML = events.map(event => {
            const start = new Date(event.start || event.start_date || event.date);
            if (Number.isNaN(start)) {
                return `<div class="col-12 text-danger small">Evento sem data válida</div>`;
            }
            const day = start.getDate();
            const month = start.toLocaleDateString('pt-BR', { month: 'short' });
            const time = start.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
            return `
                <div class="col-md-6">
                <div class="event-card">
                    <div class="d-flex align-items-center">
                    <div class="event-date">
                        <div class="day">${day}</div>
                        <div class="month">${month}</div>
                    </div>
                    <div class="ms-3 flex-grow-1">
                        <h6 class="mb-1">${event.title}</h6>
                        <p class="text-muted mb-0">${event.description || 'Sem descrição'}</p>
                        <small class="text-muted"><i class="fas fa-clock me-1"></i>${time}</small>
                    </div>
                    </div>
                </div>
                </div>
            `;
        }).join('');
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
        
        // Mapear tipos de atividade para ícones e cores
        const activityTypes = {
            'employee_created': { icon: 'user-plus', color: 'success' },
            'document_uploaded': { icon: 'file-upload', color: 'info' },
            'document_created': { icon: 'file-alt', color: 'primary' },
            'event_created': { icon: 'calendar-plus', color: 'warning' },
            'restaurant_created': { icon: 'store', color: 'danger' }
        };
        
        container.innerHTML = this.activities.map(activity => {
            const typeInfo = activityTypes[activity.activity_type] || { icon: 'info-circle', color: 'secondary' };
            const timeText = activity.created_at_relative || this.formatRelativeTime(activity.created_at);
            
            return `
                <div class="activity-item">
                    <div class="activity-icon bg-${typeInfo.color}">
                        <i class="fas fa-${typeInfo.icon}"></i>
                    </div>
                    <div class="activity-content">
                        <div class="activity-title">${activity.description || 'Atividade registrada'}</div>
                        <div class="activity-meta">
                            ${activity.restaurant_name ? `<span class="badge bg-light text-dark me-2"><i class="fas fa-store me-1"></i>${activity.restaurant_name}</span>` : ''}
                            <span class="text-muted"><i class="fas fa-clock me-1"></i>${timeText}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },
    
    /**
     * Formatar tempo relativo (ex: "2 horas atrás")
     */
    formatRelativeTime(timestamp) {
        if (!timestamp) return 'Data desconhecida';
        
        const now = new Date();
        const time = new Date(timestamp);
        
        // Verificar se a data é válida
        if (isNaN(time.getTime())) {
            return 'Data inválida';
        }
        
        const diff = now - time;
        
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (seconds < 60) return 'Agora mesmo';
        if (minutes < 60) return `${minutes} minuto${minutes > 1 ? 's' : ''} atrás`;
        if (hours < 24) return `${hours} hora${hours > 1 ? 's' : ''} atrás`;
        if (days < 7) return `${days} dia${days > 1 ? 's' : ''} atrás`;
        
        // Se for mais de 7 dias, mostrar a data formatada
        return time.toLocaleDateString('pt-BR');
    },
    
    /**
     * Exportar dados
     */
    async exportData() {
        try {
            appState.notify('Iniciando exportação de dados...', 'info');
            // TODO: Implementar exportação (CSV, PDF, etc)
        } catch (error) {
            appState.notify('Erro ao exportar dados', 'error');
        }
    }
};
