/**
 * MAC Calendar - Calendar Module
 * Módulo para gerenciar eventos do calendário
 */

const CalendarModule = {
    events: [],
    currentMonth: new Date(),
    currentDate: new Date(),
    
    /**
     * Inicializar o módulo
     */
    init() {
        console.log('📅 Inicializando Calendar Module...');
        this.setupHandlers();
        this.loadEvents();
    },
    
    /**
     * Setup event handlers
     */
    setupHandlers() {
        // Handlers dos botões podem ser configurados aqui
    },
    
    /**
     * Carregar eventos
     */
    async loadEvents() {
        try {
            const dateStr = this.currentDate.toISOString().split('T')[0];
            this.events = await api.get(`/calendar/events?date=${dateStr}`);
            this.renderCalendar();
        } catch (error) {
            console.error('❌ Erro ao carregar eventos:', error);
            appState.notify('Erro ao carregar eventos', 'error');
        }
    },
    
    /**
     * Renderizar calendário
     */
    renderCalendar() {
        // Será implementado conforme necessário
        console.log('📅 Eventos carregados:', this.events.length);
    },
    
    /**
     * Deletar evento
     */
    async deleteEvent(id) {
        if (confirm('Tem certeza que deseja deletar este evento?')) {
            try {
                await api.delete(`/calendar/events/${id}`);
                appState.notify('Evento deletado com sucesso', 'success');
                this.loadEvents();
            } catch (error) {
                console.error('Erro ao deletar evento:', error);
                appState.notify('Erro ao deletar evento', 'error');
            }
        }
    },
    
    /**
     * Criar evento
     */
    async createEvent(eventData) {
        try {
            await api.post('/calendar/events', eventData);
            appState.notify('Evento criado com sucesso', 'success');
            this.loadEvents();
        } catch (error) {
            console.error('Erro ao criar evento:', error);
            appState.notify('Erro ao criar evento', 'error');
        }
    }
};

/**
 * Salvar evento (novo ou editado)
 */
async function saveEvent() {
    const form = document.getElementById('eventForm');
    if (!form) {
        console.error('Formulário de evento não encontrado');
        alert('Erro: formulário não encontrado');
        return;
    }
    
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    try {
        const eventId = document.getElementById('eventId')?.value;
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        
        // Mapear category para event_type (conforme esperado pela API)
        if (data.category) {
            data.event_type = data.category;
            delete data.category;
        }
        
        // Converter dates
        if (data.startDate) {
            data.start_date = new Date(data.startDate).toISOString();
        }
        if (data.endDate) {
            data.end_date = new Date(data.endDate).toISOString();
        }
        
        // Remover campos desnecessários
        delete data.eventId;
        delete data.startDate;
        delete data.endDate;
        
        // Mapear checkboxes booleanos
        data.is_all_day = data.allDay === 'on';
        data.is_recurring = data.recurring === 'on';
        delete data.allDay;
        delete data.recurring;
        
        console.log('📝 Salvando evento:', data);
        
        let response;
        let message;
        if (eventId && eventId !== '') {
            // Atualizar
            response = await api.put(`/calendar/events/${eventId}`, data);
            message = 'Evento atualizado com sucesso';
        } else {
            // Criar novo
            response = await api.post('/calendar/events', data);
            message = 'Evento criado com sucesso';
        }
        
        console.log('✅ Resposta:', response);
        
        // Mostrar notificação
        if (typeof appState !== 'undefined' && appState.notify) {
            appState.notify(message, 'success');
        } else if (typeof App !== 'undefined' && App.notify) {
            App.notify(message, 'success');
        } else {
            alert(message);
        }
        
        // Fechar modal
        const modal = document.getElementById('eventModal');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        }
        
        // Resetar form
        form.reset();
        
        // Recarregar eventos
        if (typeof CalendarModule !== 'undefined') {
            CalendarModule.loadEvents();
        }
        
    } catch (error) {
        console.error('❌ Erro ao salvar evento:', error);
        const errorMsg = error.message || 'Erro ao salvar evento';
        
        if (typeof appState !== 'undefined' && appState.notify) {
            appState.notify(errorMsg, 'error');
        } else if (typeof App !== 'undefined' && App.notify) {
            App.notify(errorMsg, 'danger');
        } else {
            alert('Erro: ' + errorMsg);
        }
    }
}

/**
 * Deletar evento (versão global)
 */
function deleteEvent() {
    const eventId = document.getElementById('eventId')?.value;
    if (!eventId) {
        console.error('ID do evento não encontrado');
        return;
    }
    
    if (!confirm('Tem certeza que deseja deletar este evento?')) {
        return;
    }
    
    CalendarModule.deleteEvent(eventId);
}
