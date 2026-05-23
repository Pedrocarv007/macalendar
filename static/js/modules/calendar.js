function calendarPage() {
  return {
    calendar: null,
    showModal: false,
    editId: null,
    filterType: '',
    filterRestaurant: '',
    restaurants: [],
    isSuperUser: isSuperRole(),
    form: { title: '', description: '', start_date: '', end_date: '', event_type: 'meeting', color: '#3B82F6', location: '', link: '', is_all_day: false, restaurant: '' },

    async init() {
      await this.$nextTick();
      if (this.isSuperUser) {
        const data = await API.get('/api/restaurants/');
        this.restaurants = Array.isArray(data) ? data : (data?.results || []);
      }
      this.calendar = new FullCalendar.Calendar(document.getElementById('calendar'), {
        initialView: 'dayGridMonth',
        locale: 'pt',
        headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,listWeek' },
        events: (info, success, failure) => this.fetchEvents(info, success, failure),
        eventClick: (info) => this.openEditFromEvent(info.event),
        dateClick: (info) => this.openCreateAtDate(info.dateStr),
        height: 'auto',
      });
      this.calendar.render();
    },

    async fetchEvents(info, success, failure) {
      const params = new URLSearchParams({ start: info.startStr, end: info.endStr });
      if (this.filterType) params.set('event_type', this.filterType);
      if (this.isSuperUser && this.filterRestaurant) params.set('restaurant_id', this.filterRestaurant);
      const data = await API.get(`/api/calendar/events?${params}`);
      // data can be an array or a paginated object {results: [...]}
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
      this.form = { title: '', description: '', start_date: '', end_date: '', event_type: 'meeting', color: '#3B82F6', location: '', link: '', is_all_day: false, restaurant: this.filterRestaurant || '' };
      this.showModal = true;
    },

    openCreateAtDate(dateStr) {
      this.openCreateModal();
      this.form.start_date = dateStr + 'T09:00';
      this.form.end_date = dateStr + 'T10:00';
    },

    openEditFromEvent(event) {
      const p = event.extendedProps;
      this.editId = event.id;
      this.form = {
        title: event.title, description: p.description || '', event_type: p.event_type,
        start_date: p.start_date?.slice(0, 16) || '', end_date: p.end_date?.slice(0, 16) || '',
        color: event.backgroundColor, location: p.location || '', link: p.link || '',
        is_all_day: p.is_all_day, restaurant: p.restaurant || '',
      };
      this.showModal = true;
    },

    async saveEvent() {
      const url = this.editId ? `/api/calendar/events/${this.editId}` : '/api/calendar/events';
      const method = this.editId ? 'put' : 'post';
      const body = { ...this.form };
      // Send null for global (all restaurants) when restaurant is empty string
      if (this.isSuperUser) {
        body.restaurant = body.restaurant || null;
      } else {
        delete body.restaurant;
      }
      const data = await API[method](url, body);
      if (data) { this.showModal = false; this.reloadEvents(); toast('Evento guardado'); }
      else toast('Erro ao guardar', 'error');
    },

    async deleteEvent() {
      if (!confirm('Apagar este evento?')) return;
      await API.delete(`/api/calendar/events/${this.editId}`);
      this.showModal = false;
      this.reloadEvents();
      toast('Evento apagado');
    },
  };
}
