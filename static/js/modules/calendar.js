function calendarPage() {
  return {
    calendar: null,
    showModal: false,
    editId: null,
    filterType: '',
    filterRestaurant: '',
    restaurants: [],
    isSuperUser: isSuperRole(),
    saving: false,
    form: { title: '', description: '', start_date: '', end_date: '', event_type: 'meeting', color: '#FFBC0D', location: '', link: '', is_all_day: false, restaurant: '', photoFile: null, photoPreview: null },

    async init() {
      await this.$nextTick();
      if (this.isSuperUser) {
        const data = await API.get('/api/restaurants/');
        this.restaurants = Array.isArray(data) ? data : (data?.results || []);
      }
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
          info.el.setAttribute(
            'title',
            title.toLocaleLowerCase('pt-PT').startsWith(`${type}:`.toLocaleLowerCase('pt-PT'))
              ? title
              : `${type}: ${title}`,
          );
        },
        height: 'auto',
      });
      this.calendar.render();
    },

    async fetchEvents(info, success, failure) {
      const params = new URLSearchParams({ start: info.startStr, end: info.endStr });
      if (this.filterType) params.set('event_type', this.filterType);
      if (this.isSuperUser && this.filterRestaurant) params.set('restaurant_id', this.filterRestaurant);
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
        color: e.color, allDay: e.is_all_day,
        extendedProps: e,
      })));
    },

    reloadEvents() { this.calendar && this.calendar.refetchEvents(); },

    openCreateModal() {
      this.editId = null;
      this.form = { title: '', description: '', start_date: '', end_date: '', event_type: 'meeting', color: '#FFBC0D', location: '', link: '', is_all_day: false, restaurant: this.filterRestaurant || '', photoFile: null, photoPreview: null };
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
        color: event.backgroundColor, location: p.location || '', link: p.link || '',
        is_all_day: p.is_all_day, restaurant: p.restaurant || '',
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
  };
}
