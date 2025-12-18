(function () {
    'use strict';

    const tg = window.Telegram && window.Telegram.WebApp;

    function mustBeInTelegram() {
        if (!tg || !tg.initData) {
            const el = document.getElementById('tg-required');
            if (el) el.style.display = 'block';
            throw new Error('telegram_required');
        }
    }

    async function api(url, options) {
        const res = await fetch(url, Object.assign(
            {
                headers: Object.assign({ 'Content-Type': 'application/json' }, (options && options.headers) || {}),
            },
            options || {}
        ));
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            const err = new Error((data && data.error) || 'request_failed');
            err.status = res.status;
            err.payload = data;
            throw err;
        }
        return data;
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function showModal(id) {
        const m = document.getElementById(id);
        if (!m) return;
        m.classList.add('open');
        m.setAttribute('aria-hidden', 'false');
    }

    function hideModal(id) {
        const m = document.getElementById(id);
        if (!m) return;
        m.classList.remove('open');
        m.setAttribute('aria-hidden', 'true');
    }

    function wireCloseButtons() {
        document.querySelectorAll('[data-close]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const modal = btn.closest('.modal');
                if (modal && modal.id) hideModal(modal.id);
            });
        });
        document.querySelectorAll('.modal').forEach((m) => {
            m.addEventListener('click', (e) => {
                if (e.target === m) hideModal(m.id);
            });
        });
    }

    function buildTimeFallback(selectEl) {
        // запасной вариант (если /api/booking/slots недоступен)
        selectEl.innerHTML = '';
        const pad = (n) => String(n).padStart(2, '0');
        for (let h = 10; h <= 21; h++) {
            for (let m = 0; m < 60; m += 15) {
                if (h === 21 && m > 0) continue;
                const v = `${pad(h)}:${pad(m)}`;
                const opt = document.createElement('option');
                opt.value = v;
                opt.textContent = v;
                selectEl.appendChild(opt);
            }
        }
    }

    async function refreshEditTimes(preferTime) {
        const editDate = document.getElementById('edit-date');
        const editTime = document.getElementById('edit-time');
        if (!editDate || !editTime) return;

        const date = (editDate.value || '').trim();
        const serviceIds = getSelectedServiceIds();
        if (!date || !serviceIds.length) {
            buildTimeFallback(editTime);
            if (preferTime) editTime.value = preferTime;
            return;
        }

        try {
            const q = encodeURIComponent(serviceIds.join(','));
            const data = await api(`/api/booking/slots?date=${encodeURIComponent(date)}&service_ids=${q}`);
            const slots = Array.isArray(data && data.slots) ? data.slots : [];

            editTime.innerHTML = '';
            const times = slots
                .map((s) => (s && s.time) || '')
                .filter((t) => t);

            if (!times.length) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'Нет доступного времени';
                editTime.appendChild(opt);
                editTime.disabled = true;
                return;
            }

            editTime.disabled = false;
            times.forEach((t) => {
                const opt = document.createElement('option');
                opt.value = t;
                opt.textContent = t;
                editTime.appendChild(opt);
            });

            const wanted = preferTime || (CURRENT_BOOKING_DETAILS && CURRENT_BOOKING_DETAILS.start_time) || '';
            if (wanted && times.includes(wanted)) {
                editTime.value = wanted;
            } else {
                editTime.value = times[0];
            }
        } catch (e) {
            // если API недоступен — просто показываем общую сетку
            editTime.disabled = false;
            buildTimeFallback(editTime);
            if (preferTime) editTime.value = preferTime;
        }
    }

    let INIT_DATA = '';
    let CURRENT_BOOKING_ID = null;
    let CURRENT_BOOKING_DETAILS = null;

    let SERVICES_CATALOG = [];

    function pad2(n) { return String(n).padStart(2, '0'); }

    function buildDefaultTimes() {
        const times = [];
        for (let h = 10; h <= 20; h++) {
            for (let m = 0; m < 60; m += 15) {
                times.push(`${pad2(h)}:${pad2(m)}`);
            }
        }
        // 20:45 already included; 21:00 start usually не нужен (упирается в конец рабочего дня)
        return times;
    }

    async function loadServicesCatalog() {
        const data = await api('/api/booking/services');
        SERVICES_CATALOG = Array.isArray(data && data.services) ? data.services : [];
        return SERVICES_CATALOG;
    }

    function fillServiceSelect(selectEl) {
        if (!selectEl) return;
        selectEl.innerHTML = '';
        SERVICES_CATALOG.forEach((s) => {
            const opt = document.createElement('option');
            opt.value = String(s.id);
            opt.textContent = `${s.name} (${Number(s.duration_min||0)} мин)`;
            selectEl.appendChild(opt);
        });
    }

    function setAvailStatus(text, isError) {
        const el = document.getElementById('avail-status');
        if (!el) return;
        el.style.display = text ? 'block' : 'none';
        el.textContent = text || '';
        el.style.color = isError ? 'var(--danger)' : '';
    }

    const AVAIL_SELECTED = new Set();

    function renderTimeGrid() {
        const grid = document.getElementById('avail-grid');
        if (!grid) return;
        grid.innerHTML = '';

        buildDefaultTimes().forEach((t) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = `time-btn ${AVAIL_SELECTED.has(t) ? 'is-on' : ''}`;
            btn.textContent = t;
            btn.addEventListener('click', () => {
                if (AVAIL_SELECTED.has(t)) AVAIL_SELECTED.delete(t);
                else AVAIL_SELECTED.add(t);
                btn.classList.toggle('is-on');
            });
            grid.appendChild(btn);
        });
    }

    function renderDatesChips(dates, activeDate) {
        const root = document.getElementById('avail-dates-chips');
        if (!root) return;
        root.innerHTML = '';
        (dates || []).slice(0, 14).forEach((d) => {
            const chip = document.createElement('button');
            chip.type = 'button';
            chip.className = `chip ${d === activeDate ? 'is-active' : ''}`;
            chip.textContent = d;
            chip.addEventListener('click', () => {
                const dateEl = document.getElementById('avail-date');
                if (dateEl) {
                    dateEl.value = d;
                    loadAvailability();
                }
            });
            root.appendChild(chip);
        });
        if (!dates || !dates.length) {
            const span = document.createElement('div');
            span.className = 'muted';
            span.textContent = 'Пока нет настроенных дат';
            root.appendChild(span);
        }
    }

    async function loadAvailabilityDates(serviceId) {
        try {
            const data = await api('/api/admin/availability/dates', {
                method: 'POST',
                body: JSON.stringify({ initData: INIT_DATA, service_id: Number(serviceId) }),
            });
            return Array.isArray(data && data.dates) ? data.dates : [];
        } catch (e) {
            return [];
        }
    }

    async function loadAvailability() {
        setAvailStatus('', false);
        const serviceEl = document.getElementById('avail-service');
        const dateEl = document.getElementById('avail-date');
        if (!serviceEl || !dateEl) return;

        const serviceId = Number(serviceEl.value);
        const date = String(dateEl.value || '').trim();
        if (!serviceId || !date) {
            AVAIL_SELECTED.clear();
            renderTimeGrid();
            return;
        }

        // chips (configured dates)
        const dates = await loadAvailabilityDates(serviceId);
        renderDatesChips(dates, date);

        // load selected slots
        AVAIL_SELECTED.clear();
        try {
            const data = await api('/api/admin/availability/get', {
                method: 'POST',
                body: JSON.stringify({ initData: INIT_DATA, service_id: serviceId, date }),
            });
            const slots = Array.isArray(data && data.slots) ? data.slots : [];
            slots.forEach((t) => AVAIL_SELECTED.add(String(t)));
        } catch (e) {
            setAvailStatus('Не удалось загрузить расписание', true);
        }

        renderTimeGrid();
    }

    async function saveAvailability() {
        const serviceEl = document.getElementById('avail-service');
        const dateEl = document.getElementById('avail-date');
        if (!serviceEl || !dateEl) return;
        const serviceId = Number(serviceEl.value);
        const date = String(dateEl.value || '').trim();
        if (!serviceId || !date) {
            setAvailStatus('Выберите услугу и дату', true);
            return;
        }

        const slots = Array.from(AVAIL_SELECTED).sort();
        if (!slots.length) {
            setAvailStatus('Вы не выбрали ни одного времени. Нажмите «Удалить дату» или выберите слоты.', true);
            return;
        }

        try {
            await api('/api/admin/availability/set', {
                method: 'POST',
                body: JSON.stringify({ initData: INIT_DATA, service_id: serviceId, date, slots }),
            });
            setAvailStatus('✅ Сохранено', false);
            const dates = await loadAvailabilityDates(serviceId);
            renderDatesChips(dates, date);
        } catch (e) {
            setAvailStatus('Ошибка сохранения', true);
        }
    }

    async function deleteAvailability() {
        const serviceEl = document.getElementById('avail-service');
        const dateEl = document.getElementById('avail-date');
        if (!serviceEl || !dateEl) return;
        const serviceId = Number(serviceEl.value);
        const date = String(dateEl.value || '').trim();
        if (!serviceId || !date) {
            setAvailStatus('Выберите услугу и дату', true);
            return;
        }

        try {
            await api('/api/admin/availability/delete', {
                method: 'POST',
                body: JSON.stringify({ initData: INIT_DATA, service_id: serviceId, date }),
            });
            AVAIL_SELECTED.clear();
            renderTimeGrid();
            setAvailStatus('Дата удалена', false);
            const dates = await loadAvailabilityDates(serviceId);
            renderDatesChips(dates, date);
        } catch (e) {
            setAvailStatus('Ошибка удаления', true);
        }
    }

    async function loadBookings() {
        const root = document.getElementById('bookings-root');
        const empty = document.getElementById('bookings-empty');
        if (!root) return;
        root.innerHTML = '';
        if (empty) empty.style.display = 'none';

        const data = await api('/api/admin/bookings/upcoming', {
            method: 'POST',
            body: JSON.stringify({ initData: INIT_DATA }),
        });
        const bookings = Array.isArray(data && data.bookings) ? data.bookings : [];
        if (!bookings.length) {
            if (empty) empty.style.display = 'block';
            return;
        }

        // group by first service name
        const groups = new Map();
        bookings.forEach((b) => {
            const key = b.primary_service || 'Услуги';
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(b);
        });

        for (const [serviceName, list] of groups.entries()) {
            const title = document.createElement('div');
            title.className = 'section-title';
            title.style.marginTop = '14px';
            title.innerHTML = `<h2>${escapeHtml(serviceName)}</h2>`;
            root.appendChild(title);

            list.forEach((b) => {
                const item = document.createElement('div');
                item.className = 'service-item';
                item.setAttribute('role', 'button');
                item.setAttribute('tabindex', '0');
                item.dataset.bookingId = String(b.id);
                const name = escapeHtml(b.user_name || 'Пользователь');
                const dt = escapeHtml(b.start_label || '—');
                const price = b.total_price != null ? `${Number(b.total_price)} ₽` : '';
                item.innerHTML = `
                    <div class="service-title">
                        <strong>#${b.id} • ${name}</strong>
                        <span class="muted">${price}</span>
                    </div>
                    <div class="service-sub">
                        <span>🗓️ ${dt}</span>
                        ${b.services_summary ? `<span>• ${escapeHtml(b.services_summary)}</span>` : ''}
                    </div>
                `;
                item.addEventListener('click', () => openBooking(b.id));
                root.appendChild(item);
            });
        }
    }

    async function openBooking(bookingId) {
        CURRENT_BOOKING_ID = bookingId;
        CURRENT_BOOKING_DETAILS = null;

        const title = document.getElementById('booking-modal-title');
        const body = document.getElementById('booking-modal-body');
        if (title) title.textContent = `Запись #${bookingId}`;
        if (body) body.textContent = 'Загрузка...';

        showModal('booking-modal');

        const data = await api('/api/admin/booking/details', {
            method: 'POST',
            body: JSON.stringify({ initData: INIT_DATA, booking_id: bookingId }),
        });

        CURRENT_BOOKING_DETAILS = data;

        const b = data && data.booking;
        const user = data && data.user;
        const services = Array.isArray(data && data.services_catalog) ? data.services_catalog : [];
        const selectedIds = new Set((data && data.selected_service_ids) || []);

        const userName = escapeHtml((user && user.full_name) || (user && user.username) || '—');
        const phone = escapeHtml((user && user.phone_number) || '—');
        const dt = escapeHtml((data && data.start_label) || '—');
        const comment = escapeHtml((b && b.comment) || '');
        const promo = escapeHtml((b && b.promo_code) || '');
        const total = b && b.total_price != null ? `${Number(b.total_price)} ₽` : '—';

        const servicesText = services
            .filter((s) => selectedIds.has(Number(s.id)))
            .map((s) => s.name)
            .join(', ');

        if (body) {
            body.innerHTML = `
                <div><strong>Пользователь:</strong> ${userName}</div>
                <div><strong>Телефон:</strong> ${phone}</div>
                <div><strong>Дата и время:</strong> ${dt}</div>
                <div><strong>Услуги:</strong> ${escapeHtml(servicesText || '—')}</div>
                <div><strong>Итого:</strong> ${escapeHtml(total)}</div>
                ${promo ? `<div><strong>Промокод:</strong> ${promo}</div>` : ''}
                ${comment ? `<div><strong>Комментарий:</strong> ${comment}</div>` : ''}
            `;
        }

        // prepare edit block
        const editBlock = document.getElementById('booking-edit-block');
        const editDate = document.getElementById('edit-date');
        const editTime = document.getElementById('edit-time');
        const editServices = document.getElementById('edit-services');
        const saveBtn = document.getElementById('save-booking');
        const toggleBtn = document.getElementById('toggle-edit');

        if (editBlock) editBlock.style.display = 'none';
        if (saveBtn) saveBtn.style.display = 'none';
        if (toggleBtn) toggleBtn.textContent = '✏️ Редактировать';

        if (editDate && data && data.start_date) editDate.value = data.start_date;
        // варианты времени берём из /api/booking/slots (учитывает занятость и доступность)
        await refreshEditTimes((data && data.start_time) || '');

        if (editDate) {
            editDate.onchange = () => refreshEditTimes();
        }

        if (editServices) {
            editServices.innerHTML = '';
            services.forEach((s) => {
                const sid = Number(s.id);
                const row = document.createElement('label');
                row.className = 'service-item';
                row.style.display = 'flex';
                row.style.gap = '10px';
                row.style.alignItems = 'center';
                row.style.cursor = 'pointer';
                row.innerHTML = `
                    <input type="checkbox" data-sid="${sid}" ${selectedIds.has(sid) ? 'checked' : ''} />
                    <div style="flex:1">
                        <div class="service-title"><strong>${escapeHtml(s.name)}</strong><span class="muted">${Number(s.price||0)} ₽</span></div>
                        <div class="service-sub"><span>⏱️ ${Number(s.duration_min||0)} мин</span>${s.description ? `<span>• ${escapeHtml(s.description)}</span>` : ''}</div>
                    </div>
                `;
                editServices.appendChild(row);
            });

            // при смене услуг обновляем список доступного времени
            editServices.querySelectorAll('input[type="checkbox"]').forEach((ch) => {
                ch.addEventListener('change', () => refreshEditTimes());
            });
        }
    }

    function getSelectedServiceIds() {
        const root = document.getElementById('edit-services');
        const out = [];
        if (!root) return out;
        root.querySelectorAll('input[type="checkbox"]').forEach((ch) => {
            if (ch.checked) {
                const sid = Number(ch.getAttribute('data-sid'));
                if (!Number.isNaN(sid)) out.push(sid);
            }
        });
        return out;
    }

    async function saveBooking() {
        const editDate = document.getElementById('edit-date');
        const editTime = document.getElementById('edit-time');
        if (!editDate || !editTime) return;
        const serviceIds = getSelectedServiceIds();
        if (!serviceIds.length) {
            alert('Выберите хотя бы одну услугу');
            return;
        }
        if (editTime.disabled || !String(editTime.value || '').trim()) {
            alert('Нет доступного времени для выбранных параметров');
            return;
        }
        await api('/api/admin/booking/update', {
            method: 'POST',
            body: JSON.stringify({
                initData: INIT_DATA,
                booking_id: CURRENT_BOOKING_ID,
                date: editDate.value,
                time: editTime.value,
                service_ids: serviceIds,
            }),
        });
        hideModal('booking-modal');
        await loadBookings();
    }

    async function addService() {
        const name = (document.getElementById('new-service-name') || {}).value || '';
        const desc = (document.getElementById('new-service-desc') || {}).value || '';
        const duration = Number((document.getElementById('new-service-duration') || {}).value || 0);
        const price = Number((document.getElementById('new-service-price') || {}).value || 0);
        const status = document.getElementById('add-service-status');
        if (status) {
            status.style.display = 'none';
            status.textContent = '';
        }

        if (!name.trim()) {
            alert('Введите название услуги');
            return;
        }
        if (!duration || duration < 15) {
            alert('Длительность должна быть не меньше 15 минут');
            return;
        }

        await api('/api/admin/services/add', {
            method: 'POST',
            body: JSON.stringify({
                initData: INIT_DATA,
                name: name.trim(),
                description: desc.trim(),
                duration_min: duration,
                price: price,
            }),
        });

        if (status) {
            status.style.display = 'block';
            status.textContent = 'Услуга добавлена. Она появится у пользователей.';
        }

        // Обновим список услуг для блока доступности
        try {
            const sel = document.getElementById('avail-service');
            const prev = sel ? sel.value : '';
            await loadServicesCatalog();
            fillServiceSelect(sel);
            if (sel && prev) sel.value = prev;
            await loadAvailability();
        } catch (e) {}
        // clear
        document.getElementById('new-service-name').value = '';
        document.getElementById('new-service-desc').value = '';
    }

    async function confirmCancel() {
        const reasonEl = document.getElementById('cancel-reason');
        const reason = (reasonEl && reasonEl.value || '').trim();
        if (!reason) {
            alert('Укажите причину');
            return;
        }
        await api('/api/admin/booking/cancel', {
            method: 'POST',
            body: JSON.stringify({ initData: INIT_DATA, booking_id: CURRENT_BOOKING_ID, reason }),
        });
        hideModal('cancel-modal');
        hideModal('booking-modal');
        await loadBookings();
    }

    function wireActions() {
        const refresh = document.getElementById('refresh-bookings');
        if (refresh) refresh.addEventListener('click', loadBookings);

        const toggleEdit = document.getElementById('toggle-edit');
        const editBlock = document.getElementById('booking-edit-block');
        const saveBtn = document.getElementById('save-booking');
        if (toggleEdit && editBlock && saveBtn) {
            toggleEdit.addEventListener('click', () => {
                const isOpen = editBlock.style.display !== 'none';
                editBlock.style.display = isOpen ? 'none' : 'block';
                saveBtn.style.display = isOpen ? 'none' : 'inline-flex';
                toggleEdit.textContent = isOpen ? '✏️ Редактировать' : '↩️ Свернуть';
            });
        }
        if (saveBtn) saveBtn.addEventListener('click', saveBooking);

        const cancelBtn = document.getElementById('cancel-booking');
        if (cancelBtn) cancelBtn.addEventListener('click', () => {
            const reasonEl = document.getElementById('cancel-reason');
            if (reasonEl) reasonEl.value = '';
            showModal('cancel-modal');
        });
        const confirmCancelBtn = document.getElementById('confirm-cancel');
        if (confirmCancelBtn) confirmCancelBtn.addEventListener('click', confirmCancel);

        const addServiceBtn = document.getElementById('add-service-btn');
        if (addServiceBtn) addServiceBtn.addEventListener('click', addService);

        // Availability UI
        const availService = document.getElementById('avail-service');
        const availDate = document.getElementById('avail-date');
        const btnAll = document.getElementById('avail-select-all');
        const btnClear = document.getElementById('avail-clear');
        const btnDel = document.getElementById('avail-delete');
        const btnSave = document.getElementById('avail-save');

        if (availService) availService.addEventListener('change', () => loadAvailability());
        if (availDate) availDate.addEventListener('change', () => loadAvailability());

        if (btnAll) {
            btnAll.addEventListener('click', () => {
                AVAIL_SELECTED.clear();
                buildDefaultTimes().forEach((t) => AVAIL_SELECTED.add(t));
                renderTimeGrid();
            });
        }
        if (btnClear) {
            btnClear.addEventListener('click', () => {
                AVAIL_SELECTED.clear();
                renderTimeGrid();
            });
        }
        if (btnDel) btnDel.addEventListener('click', deleteAvailability);
        if (btnSave) btnSave.addEventListener('click', saveAvailability);
    }

    async function init() {
        mustBeInTelegram();
        wireCloseButtons();
        wireActions();

        INIT_DATA = tg.initData || '';

        const me = await api('/api/admin/me', {
            method: 'POST',
            body: JSON.stringify({ initData: INIT_DATA }),
        });

        const guard = document.getElementById('admin-guard');
        const availabilityContent = document.getElementById('availability-content');
        const adminContent = document.getElementById('admin-content');
        const servicesContent = document.getElementById('services-content');

        if (!me || !me.is_admin) {
            if (guard) guard.style.display = 'block';
            if (availabilityContent) availabilityContent.style.display = 'none';
            if (adminContent) adminContent.style.display = 'none';
            if (servicesContent) servicesContent.style.display = 'none';
            return;
        }

        if (guard) guard.style.display = 'none';
        if (availabilityContent) availabilityContent.style.display = 'block';
        if (adminContent) adminContent.style.display = 'block';
        if (servicesContent) servicesContent.style.display = 'block';

        try { tg.expand(); } catch (e) {}

        // init availability block
        try {
            await loadServicesCatalog();
            fillServiceSelect(document.getElementById('avail-service'));

            const dEl = document.getElementById('avail-date');
            if (dEl) {
                const today = new Date().toLocaleDateString('en-CA');
                dEl.min = today;
                if (!dEl.value) dEl.value = today;
            }

            renderTimeGrid();
            await loadAvailability();
        } catch (e) {
            setAvailStatus('Не удалось загрузить список услуг', true);
        }

        await loadBookings();
    }

    document.addEventListener('DOMContentLoaded', () => {
        init().catch((e) => console.error(e));
    });
})();
