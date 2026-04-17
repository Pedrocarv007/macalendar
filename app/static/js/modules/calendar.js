/**
 * ============================================================
 * 1. CONFIGURAÇÃO E ESTADO GLOBAL
 * ============================================================
 */
const CalendarConfig = {
    baseUrl: window.API_BASE_URL || '/api',
    defaultImg: 'https://www.thecarv.com/desafio.jpg'
};

const CalendarState = {
    currentDate: new Date(),
    events: [],
    viewType: 'month',
    selectedDateOnly: null,
    openFromCalendar: false,
    openFromEdit: false,
    activeEvent: null
};

/**
 * ============================================================
 * 2. SERVIÇOS (API)
 * ============================================================
 */
const CalendarService = {
    async request(url, method = 'GET', body = null) {
        const token = window.localStorage.getItem('access_token');
        const options = {
            method,
            headers: { 'Authorization': token ? `Bearer ${token}` : '' }
        };
        if (body && !(body instanceof FormData)) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        } else if (body) {
            options.body = body;
        }

        const response = await fetch(`${CalendarConfig.baseUrl}${url}`, options);
        // Handle empty response for 204 No Content (common in Delete)
        if (response.status === 204) return null;

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Erro na requisição');
        return data;
    },

    getEvents(month, year) { return this.request(`/calendar/events?month=${month + 1}&year=${year}`); },
    saveEvent(formData) { return this.request('/calendar/events', 'POST', formData); },
    deleteEvent(id) { return this.request(`/calendar/events/${id}`, 'DELETE'); },
    markPosted(id) { return this.request(`/calendar/events/${id}/mark-posted`, 'PUT'); }
};

/**
 * ============================================================
 * 3. UTILITÁRIOS
 * ============================================================
 */
const Utils_date = {
    normalizeHour: (time) => {
        const h = time?.split(':')[0] || '00';
        return `${String(Math.max(0, Math.min(23, parseInt(h)))).padStart(2, '0')}:00`;
    },
    formatDate: (d) => new Date(d).toLocaleDateString('pt-BR'),
    isSameDay: (d1, d2) => d1.getDate() === d2.getDate() && d1.getMonth() === d2.getMonth() && d1.getFullYear() === d2.getFullYear()
};

/**
 * ============================================================
 * 4. CONTROLE DE INTERFACE (UI)
 * ============================================================
 */
const CalendarUI = {
    state: CalendarState,

    async init() {
        this.bindEvents();
        await this.loadEvents();
        updateCurrentMonth();
    },

    async loadEvents() {
        const container = document.getElementById('calendarGrid');
        if (container) container.innerHTML = '<div class="col-12 text-center py-5"><div class="spinner-border text-primary"></div><p>Carregando eventos...</p></div>';
        
        try {
            const data = await CalendarService.getEvents(this.state.currentDate.getMonth(), this.state.currentDate.getFullYear());
            this.state.events = data.events || data.items || data || [];
            renderCalendar();
            renderCategoryCounts();
        } catch (err) {
            if (container) container.innerHTML = '<p class="text-danger text-center">Erro ao carregar dados.</p>';
        }
    },

    bindEvents() {
        document.querySelectorAll('input[name="viewType"]').forEach(r => {
            r.addEventListener('change', (e) => {
                this.state.viewType = e.target.id.replace('View', '');
                renderCalendar();
            });
        });

        document.getElementById('eventModal')?.addEventListener('show.bs.modal', (e) => this.handleEventModalShow(e));
        
        ['startTime', 'endTime'].forEach(id => {
            document.getElementById(id)?.addEventListener('blur', (e) => {
                e.target.value = Utils_date.normalizeHour(e.target.value);
                updateHiddenDateTimes();
            });
        });

        document.getElementById('category')?.addEventListener('change', toggleBirthdayFields);
    },

    handleEventModalShow(event) {
        if (this.state.openFromCalendar || this.state.openFromEdit) {
            updateHiddenDateTimes();
            return;
        }
        document.getElementById('eventForm').reset();
        document.getElementById('eventId').value = '';
        setSelectedDateForModal(new Date());
        setTimeFields('09:00', '10:00');
        updateHiddenDateTimes();
        toggleBirthdayFields();
    },

    syncDateTime() { updateHiddenDateTimes(); }
};

/**
 * ============================================================
 * 5. RENDERIZAÇÃO DAS VISÕES
 * ============================================================
 */
function renderCalendar() {
    const container = document.getElementById('calendarGrid');
    if (!container) return;
    container.innerHTML = '';

    if (CalendarState.viewType !== 'day') {
        ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'].forEach(day => {
            const h = document.createElement('div');
            h.className = 'day-header';
            h.textContent = day;
            container.appendChild(h);
        });
    }

    if (CalendarState.viewType === 'month') renderMonthView(container);
    else if (CalendarState.viewType === 'week') renderWeekView(container);
    else renderDayView(container);
}

function renderMonthView(container) {
    const year = CalendarState.currentDate.getFullYear();
    const month = CalendarState.currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    for (let i = 0; i < 42; i++) {
        const d = new Date(startDate);
        d.setDate(startDate.getDate() + i);
        container.appendChild(createDayCell(d, month));
    }
}

function renderWeekView(container) {
    const startOfWeek = new Date(CalendarState.currentDate);
    startOfWeek.setDate(CalendarState.currentDate.getDate() - CalendarState.currentDate.getDay());
    for (let i = 0; i < 7; i++) {
        const d = new Date(startOfWeek);
        d.setDate(startOfWeek.getDate() + i);
        container.appendChild(createDayCell(d, CalendarState.currentDate.getMonth()));
    }
}

function renderDayView(container) {
    const cell = createDayCell(CalendarState.currentDate, CalendarState.currentDate.getMonth());
    cell.classList.add('day-view-focus');
    container.appendChild(cell);
}

function createDayCell(date, currentMonth) {
    const cell = document.createElement('div');
    cell.className = `calendar-day ${date.getMonth() !== currentMonth ? 'other-month' : ''} ${Utils_date.isSameDay(date, new Date()) ? 'today' : ''}`;
    cell.innerHTML = `<div class="day-number">${date.getDate()}</div><div class="day-events"></div>`;
    cell.onclick = () => selectDate(date);

    const dayEvents = CalendarState.events.filter(e => Utils_date.isSameDay(new Date(e.start), date));
    const evContainer = cell.querySelector('.day-events');

    dayEvents.forEach(e => {
        const div = document.createElement('div');
        div.className = `event event-${e.extendedProps?.event_type || 'default'}`;
        div.textContent = e.title;
        // Logic for click: previewing the event
        div.onclick = (ex) => { 
            ex.stopPropagation(); 
            previewEvent(e); 
        };
        evContainer.appendChild(div);
    });

    return cell;
}
    // Preview de evento: mostra imagem (se houver) e descrição
    function previewEvent(event) {
        // Save active event for modal actions
        CalendarState.activeEvent = event;

        // Preenche título e data
        document.getElementById('detailsTitle').textContent = event.title || '';
        document.getElementById('detailsWhen').textContent = event.start ? Utils_date.formatDate(event.start) : '';
        document.getElementById('detailsCategory').textContent = event.extendedProps?.event_type || '';
        // Descrição
        document.getElementById('detailsDescription').textContent = event.description || event.extendedProps?.description || '';
        
        // Imagem/link
        const imgWrapper = document.getElementById('detailsImageWrapper');
        const img = document.getElementById('detailsImage');
        
        // Verifica location na raiz ou em extendedProps
        // Backend envia em extendedProps.location, mas FullCalendar pode não mapear para raiz automaticamente
        let fileUrl = event.location || event.extendedProps?.location || '';
        
        if (fileUrl && (fileUrl.endsWith('.png') || fileUrl.endsWith('.jpg') || fileUrl.endsWith('.jpeg') || fileUrl.endsWith('.webp'))) {
            let src = fileUrl;
            if (!src.startsWith('http')) {
                // Remove barra inicial se houver
                if (src.startsWith('/')) src = src.substring(1);
                // Adiciona static se não tiver
                if (!src.startsWith('mac/static/')) src = 'mac/static/' + src;
                // Adiciona barra inicial para caminho absoluto
                src = '/' + src;
            }
            img.src = src;
            imgWrapper.style.display = '';
        } else {
            imgWrapper.style.display = 'none';
        }
        // Verifica status de postado dos metadados ou cor
        const isPosted = event.extendedProps?.is_posted === true || event.backgroundColor === '#2ecc71';
        
        const btnPosted = document.getElementById('detailsMarkPosted');
        if (btnPosted) {
            if (isPosted) {
                btnPosted.innerHTML = '<i class="fas fa-check-double me-1"></i>Postado';
                btnPosted.classList.replace('btn-outline-success', 'btn-success');
                btnPosted.disabled = true;
            } else {
                btnPosted.innerHTML = '<i class="fas fa-check me-1"></i>Marcar como postado';
                btnPosted.classList.replace('btn-success', 'btn-outline-success');
                btnPosted.classList.remove('btn-success'); // garantir remoção
                btnPosted.classList.add('btn-outline-success');
                btnPosted.disabled = false;
            }
        }

        // Link
        // Abre modal
        bootstrap.Modal.getOrCreateInstance(document.getElementById('eventDetailsModal')).show();
    }

function selectDate(date) {
    CalendarState.openFromCalendar = true;
    CalendarState.openFromEdit = false;
    setSelectedDateForModal(date);
    setTimeFields('09:00', '10:00');
    updateHiddenDateTimes();
    const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('eventModal'));
    document.getElementById('eventModalTitle').textContent = 'Novo Evento - ' + Utils_date.formatDate(date);
    modal.show();
}

function editEvent(event) {
    CalendarState.openFromEdit = true;
    CalendarState.openFromCalendar = false;
    document.getElementById('eventModalTitle').textContent = 'Editar Evento';
    document.getElementById('eventId').value = event.id;
    document.getElementById('title').value = event.title;
    document.getElementById('description').value = event.description || '';
    
    const start = new Date(event.start);
    const end = event.end ? new Date(event.end) : start;
    setSelectedDateForModal(start);
    setTimeFields(String(start.getHours()).padStart(2, '0') + ':00', String(end.getHours()).padStart(2, '0') + ':00');
    document.getElementById('category').value = event.extendedProps?.event_type || 'event';
    
    updateHiddenDateTimes();
    toggleBirthdayFields();
    bootstrap.Modal.getOrCreateInstance(document.getElementById('eventModal')).show();
}

function toggleBirthdayFields() {
    const category = document.getElementById('category')?.value;
    const box = document.getElementById('birthdayFields');
    if (box) box.style.display = (category === 'birthday_party') ? '' : 'none';
}

async function saveEvent() {
    const formData = new FormData(document.getElementById('eventForm'));
    formData.set('start_date', document.getElementById('startDate').value);
    formData.set('end_date', document.getElementById('endDate').value);
    try {
        await CalendarService.saveEvent(formData);
        bootstrap.Modal.getInstance(document.getElementById('eventModal'))?.hide();
        await CalendarUI.loadEvents();
    } catch (err) { alert(err.message); }
}

async function deleteEvent() {
    const id = document.getElementById('eventId').value;
    if (!id) return;
    if (!confirm('Tem certeza que deseja excluir este evento?')) return;
    
    try {
        await CalendarService.deleteEvent(id);
        bootstrap.Modal.getInstance(document.getElementById('eventModal'))?.hide();
        await CalendarUI.loadEvents();
    } catch (err) { alert(err.message); }
}

async function deleteEventFromDetails() {
    const event = CalendarState.activeEvent;
    if (!event || !event.id) return;
    if (!confirm('Tem certeza que deseja excluir este evento?')) return;

    try {
        await CalendarService.deleteEvent(event.id);
        bootstrap.Modal.getInstance(document.getElementById('eventDetailsModal'))?.hide();
        await CalendarUI.loadEvents();
    } catch (err) { alert(err.message); }
}

function editEventFromDetails() {
    const event = CalendarState.activeEvent;
    if (!event) return;
    
    bootstrap.Modal.getInstance(document.getElementById('eventDetailsModal'))?.hide();
    editEvent(event);
}

async function markPostedFromDetails() {
    const event = CalendarState.activeEvent;
    if (!event || !event.id) return;

    try {
        await CalendarService.markPosted(event.id);
        
        // Atualizar UI localmente ou recarregar
        const btn = document.getElementById('detailsMarkPosted');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-check-double me-1"></i>Postado';
            btn.classList.replace('btn-outline-success', 'btn-success');
            btn.disabled = true;
        }
        
        // Recarrega eventos para atualizar cor no calendário
        await CalendarUI.loadEvents();
        
    } catch (err) { alert(err.message); }
}

async function markPostedFromModal() {
    // Busca ID do campo hidden do modal de edição
    const eventId = document.getElementById('eventId').value;
    if (!eventId) return;

    try {
        await CalendarService.markPosted(eventId);
        bootstrap.Modal.getInstance(document.getElementById('eventModal'))?.hide();
        await CalendarUI.loadEvents();
    } catch (err) { alert(err.message); }
}

/**
 * ============================================================
 * 7. APOIO E NAVEGAÇÃO
 * ============================================================
 */
function updateHiddenDateTimes() {
    const dateStr = CalendarState.selectedDateOnly;
    const start = Utils_date.normalizeHour(document.getElementById('startTime')?.value);
    const end = Utils_date.normalizeHour(document.getElementById('endTime')?.value);
    document.getElementById('startDate').value = `${dateStr}T${start}`;
    document.getElementById('endDate').value = `${dateStr}T${end}`;
}

function setSelectedDateForModal(date) {
    const d = new Date(date);
    CalendarState.selectedDateOnly = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    if (document.getElementById('selectedDate')) document.getElementById('selectedDate').value = CalendarState.selectedDateOnly;
}

function setTimeFields(s, e) {
    if (document.getElementById('startTime')) document.getElementById('startTime').value = s;
    if (document.getElementById('endTime')) document.getElementById('endTime').value = e;
}

function updateCurrentMonth() {
    const monthNames = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
    const el = document.getElementById('currentMonth');
    if (el) el.innerHTML = `<i class="fas fa-calendar me-2"></i> ${monthNames[CalendarState.currentDate.getMonth()]} ${CalendarState.currentDate.getFullYear()}`;
}

function renderCategoryCounts() {
    const counts = { meeting: 0, training: 0, event: 0, urgent: 0, desafio_misterio: 0, desafio_misterio_resposta: 0 };
    CalendarState.events.forEach(ev => {
        const type = ev.extendedProps?.event_type || 'event';
        if (counts[type] !== undefined) counts[type]++;
    });
    Object.keys(counts).forEach(key => {
        const el = document.getElementById(`cat-${key.replace('_', '-')}`);
        if (el) el.textContent = counts[key];
    });
}

async function nextMonth() { CalendarState.currentDate.setMonth(CalendarState.currentDate.getMonth() + 1); await CalendarUI.loadEvents(); updateCurrentMonth(); }
async function prevMonth() { CalendarState.currentDate.setMonth(CalendarState.currentDate.getMonth() - 1); await CalendarUI.loadEvents(); updateCurrentMonth(); }
async function today() { CalendarState.currentDate = new Date(); await CalendarUI.loadEvents(); updateCurrentMonth(); }

// Expose functions to global scope
window.nextMonth = nextMonth;
window.prevMonth = prevMonth;
window.today = today;
window.saveEvent = saveEvent;
window.editEventFromDetails = editEventFromDetails;
window.deleteEventFromDetails = deleteEventFromDetails;
window.markPostedFromDetails = markPostedFromDetails;
window.markPostedFromModal = markPostedFromModal;
window.deleteEvent = deleteEvent;

document.addEventListener('DOMContentLoaded', () => CalendarUI.init());