(function () {
    const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
    const guardCard = document.getElementById('admin-guard');
    const panelsCard = document.getElementById('admin-panels');
    const bookingsCard = document.getElementById('bookings-card');
    const bookingsList = document.getElementById('bookings-list');

    const settingsService = document.getElementById('settings-service');
    const settingsDates = document.getElementById('settings-dates');
    const settingsTimes = document.getElementById('settings-times');
    const settingsSave = document.getElementById('settings-save');
    const settingsStatus = document.getElementById('settings-status');

    const serviceName = document.getElementById('service-name');
    const servicePrice = document.getElementById('service-price');
    const serviceDuration = document.getElementById('service-duration');
    const serviceDescription = document.getElementById('service-description');
    const serviceAdd = document.getElementById('service-add');
    const serviceStatus = document.getElementById('service-status');

    const modal = document.getElementById('booking-modal');
    const modalBody = document.getElementById('modal-body');
    const modalTitle = document.getElementById('modal-title');
    const modalCancel = document.getElementById('modal-cancel');
    const modalReschedule = document.getElementById('modal-reschedule');

    let bootstrap = { services: [], settings: {}, bookings: [] };
    let currentBookingId = null;

    function getInitData() {
        return tg ? tg.initData || '' : '';
    }

    async function api(url, options) {
        const res = await fetch(url, Object.assign({
            headers: Object.assign({ 'Content-Type': 'application/json' }, (options && options.headers) || {}),
        }, options || {}));
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            const err = new Error((data && data.error) || 'request_failed');
            err.status = res.status;
            err.payload = data;
            throw err;
        }
        return data;
    }

    function money(val) {
        const num = Number(val || 0);
        return `${num.toLocaleString('ru-RU')} ₽`;
    }

    function formatDate(ts) {
        if (!ts) return '—';
        const dt = new Date(Number(ts) * 1000);
        return dt.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    function groupBookings(bookings) {
        const groups = {};
        bookings.forEach((b) => {
            const firstService = Array.isArray(b.services) && b.services.length ? b.services[0] : null;
            const key = firstService ? firstService.name : 'Без названия';
            if (!groups[key]) groups[key] = [];
            groups[key].push(b);
        });
        return groups;
    }

    function renderServicesSelect() {
        if (!settingsService) return;
        settingsService.innerHTML = '';
        bootstrap.services.forEach((srv) => {
            const opt = document.createElement('option');
            opt.value = srv.id;
            opt.textContent = srv.name;
            settingsService.appendChild(opt);
        });
        applySettingsValues();
    }

    function applySettingsValues() {
        const sid = Number(settingsService.value);
        const cfg = bootstrap.settings[sid] || {};
        settingsDates.value = (cfg.allowed_dates || []).join(', ');
        settingsTimes.value = (cfg.allowed_times || []).join(', ');
    }

    function renderBookings() {
        if (!bookingsList) return;
        bookingsList.innerHTML = '';
        const groups = groupBookings(bootstrap.bookings || []);
        const groupNames = Object.keys(groups);
        if (!groupNames.length) {
            bookingsList.innerHTML = '<div class="muted">Нет будущих записей</div>';
            return;
        }
        groupNames.forEach((name) => {
            const header = document.createElement('div');
            header.className = 'booking-card';
            const title = document.createElement('h4');
            title.innerHTML = `🧾 ${name}`;
            header.appendChild(title);
            groups[name].forEach((b) => {
                const card = document.createElement('div');
                card.className = 'booking-meta';
                card.innerHTML = `
                    <div><span class="badge-accent">ID ${b.id}</span> ${formatDate(b.start_ts)}</div>
                    <div>Стоимость: ${money(b.total_price)}</div>
                    <div>Клиент: ${(b.user_profile && b.user_profile.full_name) || '—'}</div>
                `;
                card.dataset.bookingId = b.id;
                card.tabIndex = 0;
                card.addEventListener('click', () => openBookingModal(b.id));
                header.appendChild(card);
            });
            bookingsList.appendChild(header);
        });
    }

    function showModal() {
        if (!modal) return;
        modal.classList.add('is-open');
        const close = modal.querySelector('[data-close]');
        if (close) close.addEventListener('click', hideModal, { once: true });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) hideModal();
        }, { once: true });
    }

    function hideModal() {
        if (!modal) return;
        modal.classList.remove('is-open');
        currentBookingId = null;
    }

    function openBookingModal(id) {
        const booking = (bootstrap.bookings || []).find((b) => Number(b.id) === Number(id));
        if (!booking) return;
        currentBookingId = booking.id;
        modalTitle.textContent = `Запись #${booking.id}`;
        const userName = (booking.user_profile && booking.user_profile.full_name) || 'Клиент';
        const servicesText = Array.isArray(booking.services)
            ? booking.services.map((s) => `${s.name} • ${s.duration_min || s.duration || ''} мин`).join('<br>')
            : '—';
        modalBody.innerHTML = `
            <div class="muted">${userName}</div>
            <div>Телефон: ${(booking.user_profile && booking.user_profile.phone_number) || '—'}</div>
            <div>Дата/время: ${formatDate(booking.start_ts)}</div>
            <div>Услуги:<br>${servicesText}</div>
            <label class="field">
                <span>Новое время</span>
                <input type="datetime-local" id="modal-datetime" />
            </label>
            <label class="field">
                <span>Комментарий для отмены/переноса</span>
                <textarea id="modal-reason" rows="3" placeholder="Опишите причину"></textarea>
            </label>
        `;
        showModal();
    }

    async function loadBootstrap() {
        const data = await api('/api/admin/bootstrap', {
            method: 'POST',
            body: JSON.stringify({ initData: getInitData() }),
        });
        bootstrap = data;
        if (guardCard) guardCard.classList.add('is-hidden');
        if (panelsCard) panelsCard.classList.remove('is-hidden');
        if (bookingsCard) bookingsCard.classList.remove('is-hidden');
        renderServicesSelect();
        renderBookings();
    }

    async function ensureAdmin() {
        try {
            const status = await api('/api/admin/status', {
                method: 'POST',
                body: JSON.stringify({ initData: getInitData() }),
            });
            if (status && status.is_admin) {
                await loadBootstrap();
            } else {
                guardCard.innerHTML = '<h3>Нет доступа</h3><p class="muted">Ваш Telegram ID не указан как администратор.</p>';
            }
        } catch (e) {
            guardCard.innerHTML = '<h3>Ошибка</h3><p class="muted">Не удалось проверить права доступа.</p>';
        }
    }

    async function saveSettings() {
        if (!settingsService) return;
        settingsStatus.textContent = '';
        const serviceId = Number(settingsService.value);
        try {
            const res = await api('/api/admin/settings', {
                method: 'POST',
                body: JSON.stringify({
                    initData: getInitData(),
                    service_id: serviceId,
                    allowed_dates: settingsDates.value.split(',').map((x) => x.trim()).filter(Boolean),
                    allowed_times: settingsTimes.value.split(',').map((x) => x.trim()).filter(Boolean),
                }),
            });
            bootstrap.settings[serviceId] = res.settings;
            settingsStatus.textContent = 'Сохранено';
        } catch (e) {
            settingsStatus.textContent = 'Не удалось сохранить';
        }
    }

    async function addService() {
        serviceStatus.textContent = '';
        try {
            const res = await api('/api/admin/service', {
                method: 'POST',
                body: JSON.stringify({
                    initData: getInitData(),
                    service: {
                        name: serviceName.value,
                        price: servicePrice.value,
                        duration_min: serviceDuration.value,
                        description: serviceDescription.value,
                    },
                }),
            });
            bootstrap.services.push(res.service);
            renderServicesSelect();
            serviceStatus.textContent = 'Добавлено';
            serviceName.value = '';
            servicePrice.value = '';
            serviceDuration.value = '';
            serviceDescription.value = '';
        } catch (e) {
            serviceStatus.textContent = 'Не удалось добавить услугу';
        }
    }

    async function cancelBooking() {
        if (!currentBookingId) return;
        const reason = document.getElementById('modal-reason')?.value || '';
        try {
            await api(`/api/admin/booking/${currentBookingId}/cancel`, {
                method: 'POST',
                body: JSON.stringify({ initData: getInitData(), reason }),
            });
            hideModal();
            await loadBootstrap();
        } catch (e) {
            alert('Не удалось отменить запись');
        }
    }

    async function rescheduleBooking() {
        if (!currentBookingId) return;
        const reason = document.getElementById('modal-reason')?.value || '';
        const dtValue = document.getElementById('modal-datetime')?.value;
        if (!dtValue) {
            alert('Укажите новое время');
            return;
        }
        const ts = Date.parse(dtValue);
        if (Number.isNaN(ts)) {
            alert('Некорректная дата');
            return;
        }
        try {
            await api(`/api/admin/booking/${currentBookingId}/reschedule`, {
                method: 'POST',
                body: JSON.stringify({ initData: getInitData(), start_ts: Math.floor(ts / 1000), reason }),
            });
            hideModal();
            await loadBootstrap();
        } catch (e) {
            alert('Не удалось перенести запись');
        }
    }

    function bindEvents() {
        if (settingsService) settingsService.addEventListener('change', applySettingsValues);
        if (settingsSave) settingsSave.addEventListener('click', saveSettings);
        if (serviceAdd) serviceAdd.addEventListener('click', addService);
        if (modalCancel) modalCancel.addEventListener('click', cancelBooking);
        if (modalReschedule) modalReschedule.addEventListener('click', rescheduleBooking);
    }

    bindEvents();
    ensureAdmin();
})();
