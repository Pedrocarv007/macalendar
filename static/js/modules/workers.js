function workersPage() {
  return {
    workers: [], loading: false,
    showDetail: false, selected: {},
    search: '', restaurantFilter: '', statusFilter: '',
    restaurants: [],
    editRestaurantId: '',
    restaurantSaving: false,
    photoUploading: false,

    async init() {
      const resData = await API.get('/api/workers/restaurants/');
      this.restaurants = Array.isArray(resData) ? resData : (resData?.results || []);
      await this.load();
    },

    async load() {
      this.loading = true;
      const params = new URLSearchParams();
      if (this.search)           params.set('search',        this.search);
      if (this.restaurantFilter) params.set('restaurant_id', this.restaurantFilter);
      const data = await API.get(`/api/workers/?${params.toString()}`);
      let workers = Array.isArray(data) ? data : (data?.results || []);
      if (this.statusFilter) {
        workers = workers.filter(w => w.training_status === this.statusFilter);
      }
      this.workers = workers;
      this.loading = false;
    },

    openDetail(w) {
      this.selected         = { ...w };
      this.editRestaurantId = w.restaurant_id || '';
      this.showDetail       = true;
    },

    async saveRestaurant() {
      if (!this.selected.id) return;
      this.restaurantSaving = true;
      const res = await API.patch(
        `/api/workers/${this.selected.id}/restaurant/`,
        { restaurant_id: this.editRestaurantId }
      );
      this.restaurantSaving = false;
      if (res && res.restaurant_name) {
        this.selected.restaurant_id   = res.restaurant_id;
        this.selected.restaurant_name = res.restaurant_name;
        // Actualiza o card na grelha também
        const idx = this.workers.findIndex(w => w.id === this.selected.id);
        if (idx !== -1) {
          this.workers[idx].restaurant_id   = res.restaurant_id;
          this.workers[idx].restaurant_name = res.restaurant_name;
        }
        toast('Restaurante guardado.');
      } else {
        toast('Erro ao guardar restaurante.', 'error');
      }
    },

    async uploadPhoto(event) {
      const file = event.target.files[0];
      if (!file || !this.selected.id) return;
      this.photoUploading = true;
      const fd = new FormData();
      fd.append('photo', file);
      const res = await API.upload(`/api/workers/${this.selected.id}/photo/`, fd);
      this.photoUploading = false;
      if (res && res.photo_url) {
        this.selected.photo_url = res.photo_url + '?t=' + Date.now();
        const idx = this.workers.findIndex(w => w.id === this.selected.id);
        if (idx !== -1) this.workers[idx].photo_url = this.selected.photo_url;
        toast('Foto atualizada.');
      } else {
        toast('Erro ao carregar foto.', 'error');
      }
      // Limpa o input para permitir re-upload do mesmo ficheiro
      event.target.value = '';
    },
  };
}
