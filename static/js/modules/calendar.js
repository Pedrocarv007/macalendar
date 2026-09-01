function calendarPage() {
  return {
    calendar: null,
    showModal: false,
    editId: null,
    filterTypes: [],
    filterRestaurant: '',
    filterImpact: '',
    filterSearch: '',
    eventTypes: [],
    restaurants: [],
    isSuperUser: isSuperRole(),
    saving: false,
    syncingExternal: false,
    form: { title: '', description: '', start_date: '', end_date: '', event_type: 'meeting', color: '#93C5FD', location: '', link: '', is_all_day: false, restaurant: '', impact_level: 'medium', impact_category: 'other', is_external: false, event_metadata: {}, photoFile: null, photoPreview: null },

    async init() {
      await this.$nextTick();
      const [optionsData, restaurantData] = await Promise.all([
        API.get('/api/calendar/events/options'),
        this.isSuperUser ? API.get('/api/restaurants/') : Promise.resolve([]),
      ]);
      this.eventTypes = optionsData?.event_types || this.fallbackEventTypes();
      this.restaurants = Array.isArray(restaurantData)
        ? restaurantData
        : (restaurantData?.results || []);
      this.calendar = new FullCalendar.Calendar(document.getElementById('calendar'), {
        initialView: 'dayGridMonth',
        locale: 'pt',
        firstDay: 1,
        nowIndicator: true,
        navLinks: true,
        selectable: true,
        selectMirror: true,
        dayMaxEvents: true,
        buttonText: {
          today: 'Hoje',
          month: 'Mês',
          week: 'Semana',
          day: 'Dia',
          list: 'Agenda',
        },
        buttonHints: {
          prev: 'Período anterior',
          next: 'Período seguinte',
          today: 'Ir para hoje',
          month: 'Abrir vista mensal',
          week: 'Abrir vista semanal',
          day: 'Abrir vista diária',
          list: 'Abrir agenda',
        },
        navLinkHint: 'Abrir $0',
        viewHint: 'Abrir vista $0',
        moreLinkHint: 'Mostrar mais eventos',
        closeHint: 'Fechar',
        timeHint: 'Hora',
        eventHint: 'Evento',
        eventTextColor: '#2D2D2D',
        headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,listWeek' },
        events: (info, success, failure) => this.fetchEvents(info, success, failure),
        eventClick: (info) => this.openEditFromEvent(info.event),
        dateClick: (info) => this.openCreateAtDate(info.dateStr),
        select: (info) => this.openCreateFromSelection(info),
        eventDidMount: (info) => {
          const type = info.event.extendedProps.event_type_label || 'Evento';
          const title = info.event.title || type;
          const impact = info.event.extendedProps.event_metadata?.impact_level;
          const impactText = {
            high: 'impacto alto',
            medium: 'impacto médio',
            low: 'impacto baixo',
          }[impact];
          const peak = info.event.extendedProps.event_metadata?.peak_window_label;
          if (info.event.extendedProps.event_type === 'birthday') {
            info.el.dataset.demoPerson = title.replace(/^anivers[aá]rio\s*[:·-]?\s*/i, '');
            info.el.dataset.demoSensitive = '';
          } else {
            info.el.dataset.demoPrivate = '';
          }
          window.TheCarvDemo?.refresh();
          info.el.setAttribute(
            'title',
            (title.toLocaleLowerCase('pt-PT').startsWith(`${type}:`.toLocaleLowerCase('pt-PT'))
              ? title
              : `${type}: ${title}`)
              + (impactText ? ` · ${impactText}` : '')
              + (peak ? ` · ${peak}` : ''),
          );
        },
        height: 'auto',
      });
      this.calendar.render();
    },

    async fetchEvents(info, success, failure) {
      const params = new URLSearchParams({ start: info.startStr, end: info.endStr });
      this.filterTypes.forEach(value => params.append('event_type', value));
      if (this.isSuperUser && this.filterRestaurant) params.set('restaurant_id', this.filterRestaurant);
      if (this.filterImpact) params.set('impact_level', this.filterImpact);
      if (this.filterSearch.trim()) params.set('search', this.filterSearch.trim());
      const data = await API.get(`/api/calendar/events?${params}`);
      if (apiError(data)) {
        failure(new Error(apiError(data)));
        toast(apiError(data), 'error');
        return;
      }
      const events = Array.isArray(data) ? data : (data?.results || []);
      success(events.map(e => ({
        id: e.id, title: e.title,
        start: e.start_date, end: e.end_date,
        color: e.color || this.colorForType(e.event_type), allDay: e.is_all_day,
        extendedProps: e,
      })));
    },

    reloadEvents() { this.calendar && this.calendar.refetchEvents(); },

    fallbackEventTypes() {
      return [
        { value: 'meeting', label: 'Reunião', color: '#93C5FD' },
        { value: 'birthday', label: 'Aniversário', color: '#FFBC0D' },
        { value: 'holiday', label: 'Feriado', color: '#FCA5A5' },
        { value: 'post', label: 'Publicação', color: '#F9A8D4' },
        { value: 'local_impact', label: 'Evento local com impacto', color: '#FDBA74' },
        { value: 'other', label: 'Outro', color: '#D4D4D8' },
      ];
    },

    colorForType(eventType) {
      return this.eventTypes.find(item => item.value === eventType)?.color || '#D4D4D8';
    },

    labelForType(eventType) {
      return this.eventTypes.find(item => item.value === eventType)?.label || 'Outro';
    },

    isTypeSelected(eventType) {
      return this.filterTypes.includes(eventType);
    },

    toggleTypeFilter(eventType) {
      this.filterTypes = this.isTypeSelected(eventType)
        ? this.filterTypes.filter(value => value !== eventType)
        : [...this.filterTypes, eventType];
      this.reloadEvents();
    },

    clearFilters() {
      this.filterTypes = [];
      this.filterRestaurant = '';
      this.filterImpact = '';
      this.filterSearch = '';
      this.reloadEvents();
    },

    hasActiveFilters() {
      return Boolean(
        this.filterTypes.length
        || this.filterRestaurant
        || this.filterImpact
        || this.filterSearch.trim(),
      );
    },

    syncFormColor() {
      this.form.color = this.colorForType(this.form.event_type);
    },

    openCreateModal() {
      this.editId = null;
      this.form = { title: '', description: '', start_date: '', end_date: '', event_type: 'meeting', color: this.colorForType('meeting'), location: '', link: '', is_all_day: false, restaurant: this.filterRestaurant || '', impact_level: 'medium', impact_category: 'other', is_external: false, event_metadata: {}, photoFile: null, photoPreview: null };
      this.showModal = true;
    },

    openCreateAtDate(dateStr) {
      this.openCreateModal();
      this.form.start_date = dateStr + 'T09:00';
      this.form.end_date = dateStr + 'T10:00';
    },

    openCreateFromSelection(info) {
      this.openCreateModal();
      this.form.start_date = this.toLocalInput(info.start);
      this.form.end_date = this.toLocalInput(info.end || new Date(info.start.getTime() + 3600000));
      this.form.is_all_day = Boolean(info.allDay);
      this.calendar?.unselect();
    },

    toLocalInput(value) {
      const date = new Date(value);
      const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
      return local.toISOString().slice(0, 16);
    },

    openEditFromEvent(event) {
      const p = event.extendedProps;
      this.editId = event.id;
      this.form = {
        title: event.title, description: p.description || '', event_type: p.event_type,
        start_date: p.start_date?.slice(0, 16) || '', end_date: p.end_date?.slice(0, 16) || '',
        color: this.colorForType(p.event_type), location: p.location || '', link: p.link || '',
        is_all_day: p.is_all_day, restaurant: p.restaurant || '',
        impact_level: p.event_metadata?.impact_level || 'medium',
        impact_category: p.event_metadata?.impact_category || 'other',
        is_external: Boolean(p.is_external),
        event_metadata: p.event_metadata || {},
        photoFile: null, photoPreview: p.photo_url || null,
      };
      this.showModal = true;
    },

    async saveEvent() {
      if (!this.form.title.trim()) {
        toast('Indique o título do evento.', 'error');
        return;
      }
      if (!this.form.start_date) {
        toast('Indique a data e hora de início.', 'error');
        return;
      }
      if (this.form.end_date && new Date(this.form.end_date) < new Date(this.form.start_date)) {
        toast('A data de fim não pode ser anterior ao início.', 'error');
        return;
      }
      this.saving = true;
      const url = this.editId ? `/api/calendar/events/${this.editId}` : '/api/calendar/events';
      const method = this.editId ? 'put' : 'post';
      const body = { ...this.form };
      delete body.photoFile;
      delete body.photoPreview;
      delete body.is_external;
      delete body.color;
      const metadata = { ...(body.event_metadata || {}) };
      if (body.event_type === 'local_impact') {
        metadata.impact_level = body.impact_level || 'medium';
        metadata.impact_category = body.impact_category || 'other';
      }
      body.event_metadata = metadata;
      delete body.impact_level;
      delete body.impact_category;
      if (this.isSuperUser) {
        body.restaurant = body.restaurant || null;
      } else {
        delete body.restaurant;
      }
      try {
        const data = await API[method](url, body);
        const error = apiError(data);
        if (error) {
          toast(error, 'error');
          return;
        }
        if (this.form.photoFile) {
          const eventId = this.editId || data.id;
          const fd = new FormData();
          fd.append('photo', this.form.photoFile);
          const photoResult = await API.upload(`/api/calendar/events/${eventId}/photo`, fd);
          const photoError = apiError(photoResult);
          if (photoError) {
            toast(`O evento foi guardado, mas a fotografia falhou: ${photoError}`, 'warning');
          }
        }
        this.showModal = false;
        this.reloadEvents();
        toast('Evento guardado com sucesso.');
      } finally {
        this.saving = false;
      }
    },

    async deleteEvent() {
      if (!confirm('Apagar este evento?')) return;
      const data = await API.delete(`/api/calendar/events/${this.editId}`);
      const error = apiError(data);
      if (error) {
        toast(error, 'error');
        return;
      }
      this.showModal = false;
      this.reloadEvents();
      toast('Evento apagado.');
    },

    async syncExternalEvents() {
      if (!this.isSuperUser || this.syncingExternal) return;
      this.syncingExternal = true;
      try {
        const data = await API.post('/api/calendar/events/sync-external', {});
        const error = apiError(data);
        if (error) {
          toast(error, 'error');
          return;
        }
        this.reloadEvents();
        toast(data.message || 'Eventos da Internet atualizados.');
      } finally {
        this.syncingExternal = false;
      }
    },
  };
}
