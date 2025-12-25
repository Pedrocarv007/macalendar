/* Notifications dropdown controller */
(function() {
    const dropdown = document.getElementById('notificationsDropdown');
    const menu = document.getElementById('notificationsMenu');
    const list = document.getElementById('notificationsList');
    const empty = document.getElementById('notificationsEmpty');
    const badge = document.getElementById('notificationsBadge');

    if (!dropdown || !menu || !list || !empty) return;

    function relativeTime(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        const diffMs = Date.now() - d.getTime();
        const diffMin = Math.floor(diffMs / 60000);
        if (diffMin < 1) return 'agora';
        if (diffMin < 60) return `${diffMin} min`;
        const diffH = Math.floor(diffMin / 60);
        if (diffH < 24) return `${diffH} h`;
        const diffD = Math.floor(diffH / 24);
        return `${diffD} d`;
    }

    async function fetchNotifications() {
        try {
            const data = await api.get('/notifications?unread_only=false&limit=10');
            const items = data.notifications || [];
            const unreadCount = data.unread_count || 0;

            // badge
            if (badge) {
                if (unreadCount > 0) {
                    badge.style.display = 'inline-block';
                    badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
                } else {
                    badge.style.display = 'none';
                }
            }

            list.innerHTML = '';
            if (!items.length) {
                empty.style.display = 'block';
                return;
            }
            empty.style.display = 'none';

            items.forEach((n) => {
                const item = document.createElement('li');
                item.innerHTML = `
                    <a class="dropdown-item" href="#">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="me-2">
                                <div class="fw-semibold">${n.title || 'Notificação'}</div>
                                ${n.message ? `<div class="small text-muted">${n.message}</div>` : ''}
                            </div>
                            <small class="text-muted">${relativeTime(n.created_at)}</small>
                        </div>
                    </a>
                `;
                list.appendChild(item);
            });

            // marca como lidas ao abrir
            const unreadIds = items.filter((n) => !n.read_at).map((n) => n.id);
            if (unreadIds.length) {
                markRead(unreadIds);
            }
        } catch (err) {
            console.error('Erro ao carregar notificações', err);
        }
    }

    async function markRead(ids) {
        try {
            await api.post('/notifications/mark-read', { notification_ids: ids });
            if (badge) badge.style.display = 'none';
        } catch (err) {
            console.error('Erro ao marcar notificações como lidas', err);
        }
    }

    dropdown.addEventListener('show.bs.dropdown', fetchNotifications);
})();
