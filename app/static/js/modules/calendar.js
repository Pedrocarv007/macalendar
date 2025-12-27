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
            // Incluir eventos globais (restaurant_id null) junto com os do restaurante
            const res = await api.get('/calendar/events?include_global=true');
            this.events = res.events || [];
            if (typeof events !== 'undefined') {
                events = this.events;
            }
            if (typeof renderCalendar === 'function') {
                renderCalendar();
                if (typeof renderTodayEvents === 'function') {
                    renderTodayEvents();
                }
                if (typeof renderUpcomingEvents === 'function') {
                    renderUpcomingEvents();
                }
                if (typeof updateCurrentMonth === 'function') {
                    updateCurrentMonth();
                }
                if (typeof renderCategoryCounts === 'function') {
                    renderCategoryCounts();
                }
            }
        } catch (error) {
            if (typeof appState !== 'undefined' && appState.notify) {
                appState.notify('Erro ao carregar eventos', 'error');
            }
        }
    },
    
    /**
     * Renderizar calendário
     */
    renderCalendar() {
        // Será implementado conforme necessário
    },
    
    /**
     * Deletar evento
     */
    async deleteEvent(id) {
        const self = this;  // Preservar contexto de 'this'
        Swal.fire({
            title: 'Deletar evento?',
            text: 'Esta ação não pode ser desfeita!',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc3545',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Sim, deletar!',
            cancelButtonText: 'Cancelar'
        }).then(async (result) => {
            if (result.isConfirmed) {
                try {
                    const response = await api.delete(`/calendar/events/${id}`);
                    Swal.fire({
                        icon: 'success',
                        title: 'Deletado!',
                        text: 'Evento deletado com sucesso',
                        timer: 1500,
                        showConfirmButton: false
                    });
                    await self.loadEvents();
                } catch (error) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Erro',
                        text: error.message || 'Erro ao deletar evento'
                    });
                }
            }
        });
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
            appState.notify('Erro ao criar evento', 'error');
        }
    },

    async generateMysteryChallenges(params) {
        try {
            const res = await api.post('/calendar/generate/mystery-tuesdays', params);
            await this.loadEvents();
            return res;
        } catch (error) {
            throw error;
        }
    },

    async generateMysteryAnswers(params) {
        try {
            const res = await api.post('/calendar/generate/mystery-answers', params);
            if (typeof appState !== 'undefined' && appState.notify) {
                appState.notify(`Geradas ${res.count || 0} respostas de sábado`, 'success');
            }
            await this.loadEvents();
        } catch (error) {
            if (typeof appState !== 'undefined' && appState.notify) {
                appState.notify(error.message || 'Erro ao gerar respostas', 'error');
            }
            throw error;
        }
    },

    async markPosted(id) {
        try {
            await api.put(`/calendar/events/${id}/mark-posted`, {});
            if (typeof appState !== 'undefined' && appState.notify) {
                appState.notify('Evento marcado como postado', 'success');
            }
            await this.loadEvents();
        } catch (error) {
            if (typeof appState !== 'undefined' && appState.notify) {
                appState.notify('Erro ao marcar postado', 'error');
            }
            throw error;
        }
    }
};

/**
 * Salvar evento (novo ou editado)
 */
async function saveEvent() {
    const form = document.getElementById('eventForm');
    if (!form) {
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
        
        // Se for festa de aniversário, incluir número de pessoas na descrição
        const peopleCount = data.peopleCount ? parseInt(data.peopleCount, 10) : null;
        if (data.event_type === 'birthday_party' && peopleCount && peopleCount > 0) {
            const prefix = `Pessoas: ${peopleCount}`;
            if (data.description) {
                // Evitar duplicar a informação
                if (!/Pessoas\s*:\s*\d+/i.test(data.description)) {
                    data.description = `${prefix}\n${data.description}`;
                }
            } else {
                data.description = prefix;
            }
        }

        // Remover campos desnecessários
        delete data.eventId;
        delete data.startDate;
        delete data.endDate;
        delete data.peopleCount;
        
        // Mapear checkboxes booleanos
        data.is_all_day = data.allDay === 'on';
        data.is_recurring = data.recurring === 'on';
        delete data.allDay;
        delete data.recurring;

        // Garantir restaurant_id: usar o do usuário da sessão se não houver no formulário
        if (!data.restaurant_id) {
            const userRest = (typeof appState !== 'undefined' && appState.user) ? appState.user.restaurant_id : null;
            if (userRest) {
                data.restaurant_id = userRest;
            }
        }
        
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
        return;
    }
    
    if (!confirm('Tem certeza que deseja deletar este evento?')) {
        return;
    }
    
    CalendarModule.deleteEvent(eventId);
}
