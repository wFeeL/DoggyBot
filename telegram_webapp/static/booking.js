(function () {
    const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
    const stateKey = 'dl_booking_state';

    function getUserId() {
        const tgId = tg && tg.initDataUnsafe && tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : null;
        if (tgId) return String(tgId);
        const qs = new URLSearchParams(window.location.search);
        return qs.get('user_id');
    }

    function getInitData() {
        return tg ? (tg.initData || '') : '';
    }

    function setState(next) {
        try {
            window.sessionStorage.setItem(stateKey, JSON.stringify(next || {}));
        } catch (e) {
            return;
        }
    }

    function getState() {
        try {
            const raw = window.sessionStorage.getItem(stateKey);
            return raw ? JSON.parse(raw) : {};
        } catch (e) {
            return {};
        }
    }

    function patchState(partial) {
        setState(Object.assign({}, getState(), partial || {}));
    }

    function clearState() {
        try {
            window.sessionStorage.removeItem(stateKey);
        } catch (e) {
            return;
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

    function money(rub) {
        const n = Number(rub || 0);
        return `${n.toLocaleString('ru-RU')} ₽`;
    }

    function minutesLabel(min) {
        const m = Number(min || 0);
        if (!m) return '—';
        const h = Math.floor(m / 60);
        const rest = m % 60;
        if (!h) return `${m} мин`;
        if (!rest) return `${h} ч`;
        return `${h} ч ${rest} мин`;
    }

    function formatDateTime(tsSeconds) {
        if (!tsSeconds) return '—';
        const dt = new Date(Number(tsSeconds) * 1000);
        return dt.toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    function showModal(id) {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.add('is-open');

        const close = el.querySelector('[data-close]');
        if (close) {
            close.addEventListener('click', () => el.classList.remove('is-open'), { once: true });
        }

        el.addEventListener(
            'click',
            (e) => {
                if (e.target === el) el.classList.remove('is-open');
            },
            { once: true }
        );
    }

    function mustBeInTelegram() {
        const msg = document.getElementById('tg-required');
        if (!msg) return;
        const tgId = tg && tg.initDataUnsafe && tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : null;
        msg.style.display = tgId ? 'none' : 'block';
    }

    async function ensureUser() {
        const initData = getInitData();
        if (!initData) return;
        await api('/api/auth/ensure_user', {
            method: 'POST',
            body: JSON.stringify({ initData }),
        });
    }

    async function hasForm() {
        const uid = getUserId();
        if (!uid) return false;
        const data = await api(`/api/profile/has_form/${encodeURIComponent(uid)}`);
        return Boolean(data && data.has_form);
    }

    function tgConfirm(message) {
        return new Promise((resolve) => {
            if (tg && typeof tg.showPopup === 'function') {
                try {
                    tg.showPopup(
                        {
                            title: 'Подтвердите',
                            message,
                            buttons: [
                                { id: 'ok', type: 'default', text: 'Да' },
                                { id: 'cancel', type: 'cancel', text: 'Отмена' },
                            ],
                        },
                        (id) => resolve(id === 'ok')
                    );
                    return;
                } catch (e) {
                    // fallback below
                }
            }
            resolve(window.confirm(message));
        });
    }

    async function initProfilePage() {
        mustBeInTelegram();
        await ensureUser();

        const startBtns = document.querySelectorAll('[data-start-booking]');
        startBtns.forEach((btn) => {
            btn.addEventListener('click', async () => {
                clearState();
                const sid = btn.getAttribute('data-service-id');
                if (sid) patchState({ service_ids: [Number(sid)] });

                const ok = await hasForm().catch(() => false);
                if (!ok) {
                    showModal('form-required-modal');
                    return;
                }
                window.location.href = '/booking/services';
            });
        });
    }

    async function initServicesPage() {
        mustBeInTelegram();
        await ensureUser();

        const ok = await hasForm().catch(() => false);
        if (!ok) {
            showModal('form-required-modal');
            return;
        }

        const root = document.getElementById('services-root');
        const searchInput = document.getElementById('service-search');
        const nextBtn = document.getElementById('next-btn');
        const sumEl = document.getElementById('summary');

        const data = await api('/api/booking/services');
        const services = Array.isArray(data && data.services) ? data.services : [];

        const state = getState();
        let selected = new Set((state.service_ids || []).map((x) => Number(x)));

        function compute() {
            let totalPrice = 0;
            let totalMin = 0;
            const chosen = [];
            services.forEach((s) => {
                if (selected.has(Number(s.id))) {
                    totalPrice += Number(s.price || 0);
                    totalMin += Number(s.duration_min || 0);
                    chosen.push(s);
                }
            });
            return { totalPrice, totalMin, chosen };
        }

        function updateFooter() {
            const { totalPrice, totalMin } = compute();
            const count = selected.size;
            nextBtn.disabled = count === 0;
            if (!sumEl) return;

            if (count) {
                sumEl.innerHTML = `<strong>${count} усл.</strong><span>${minutesLabel(totalMin)} • ${money(totalPrice)}</span>`;
            } else {
                sumEl.innerHTML = `<strong>Выберите услуги</strong><span>Можно выбрать несколько</span>`;
            }
        }

        function render(list) {
            if (!root) return;
            root.innerHTML = '';
            if (!list.length) {
                root.innerHTML = '<div class="empty">Ничего не найдено</div>';
                updateFooter();
                return;
            }

            list.forEach((s) => {
                const isSel = selected.has(Number(s.id));
                const el = document.createElement('div');
                el.className = `service-item with-check ${isSel ? 'is-selected' : ''}`;
                el.setAttribute('role', 'button');
                el.setAttribute('tabindex', '0');
                el.innerHTML = `
                    <span class="service-check" aria-hidden="true"></span>
                    <div class="service-body">
                        <div class="service-title">
                            <strong>${escapeHtml(s.name)}</strong>
                            <span class="muted">${money(s.price)}</span>
                        </div>
                        <div class="service-sub">
                            <span>⏱️ ${minutesLabel(s.duration_min)}</span>
                            ${s.description ? `<span>• ${escapeHtml(s.description)}</span>` : ''}
                        </div>
                    </div>
                `;

                const toggle = () => {
                    const id = Number(s.id);
                    if (selected.has(id)) selected.delete(id);
                    else selected.add(id);
                    render(currentList());
                };

                el.addEventListener('click', toggle);
                el.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        toggle();
                    }
                });

                root.appendChild(el);
            });

            updateFooter();
        }

        function currentList() {
            const q = (searchInput && searchInput.value ? searchInput.value : '').trim().toLowerCase();
            return !q ? services : services.filter((s) => String(s.name || '').toLowerCase().includes(q));
        }

        if (searchInput) searchInput.addEventListener('input', () => render(currentList()));

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                patchState({ service_ids: Array.from(selected), start_ts: null });
                window.location.href = '/booking/time';
            });
        }

        render(currentList());
    }

    async function initTimePage() {
        mustBeInTelegram();
        await ensureUser();

        const ok = await hasForm().catch(() => false);
        if (!ok) {
            showModal('form-required-modal');
            return;
        }

        const state = getState();
        if (!Array.isArray(state.service_ids) || !state.service_ids.length) {
            window.location.href = '/booking/services';
            return;
        }

        const dateInput = document.getElementById('date');
        const slotsRoot = document.getElementById('slots-root');
        const nextBtn = document.getElementById('next-btn');
        const info = document.getElementById('info');

        const today = new Date();
        const min = today.toISOString().slice(0, 10);
        if (dateInput) {
            dateInput.min = min;
            if (!dateInput.value) dateInput.value = min;
        }

        let selectedStartTs = state.start_ts ? Number(state.start_ts) : null;

        async function loadSlots() {
            if (nextBtn) nextBtn.disabled = true;
            if (slotsRoot) slotsRoot.innerHTML = '<div class="skeleton">Загружаем свободное время…</div>';

            const date = dateInput ? dateInput.value : min;
            const ids = state.service_ids.map((x) => Number(x)).join(',');
            const data = await api(`/api/booking/slots?date=${encodeURIComponent(date)}&service_ids=${encodeURIComponent(ids)}`);
            const slots = Array.isArray(data && data.slots) ? data.slots : [];

            if (info) info.textContent = `Длительность: ${minutesLabel(data && data.duration_min ? data.duration_min : 0)}`;

            if (!slotsRoot) return;
            slotsRoot.innerHTML = '';

            if (!slots.length) {
                slotsRoot.innerHTML = '<div class="empty">Свободных слотов на эту дату нет</div>';
                return;
            }

            slots.forEach((sl) => {
                const ts = Number(sl.start_ts);
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = `slot ${selectedStartTs === ts ? 'is-selected' : ''}`;
                btn.textContent = sl.label;

                btn.addEventListener('click', () => {
                    selectedStartTs = ts;
                    patchState({ start_ts: ts });
                    Array.from(slotsRoot.querySelectorAll('.slot')).forEach((b) => b.classList.remove('is-selected'));
                    btn.classList.add('is-selected');
                    if (nextBtn) nextBtn.disabled = false;
                });

                slotsRoot.appendChild(btn);
            });

            if (selectedStartTs && nextBtn) nextBtn.disabled = false;
        }

        if (dateInput) {
            dateInput.addEventListener('change', async () => {
                selectedStartTs = null;
                patchState({ start_ts: null });
                await loadSlots();
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (!selectedStartTs) return;
                window.location.href = '/booking/comment';
            });
        }

        await loadSlots();
    }

    async function initCommentPage() {
        mustBeInTelegram();
        await ensureUser();

        const ok = await hasForm().catch(() => false);
        if (!ok) {
            showModal('form-required-modal');
            return;
        }

        const state = getState();
        if (!Array.isArray(state.service_ids) || !state.service_ids.length) {
            window.location.href = '/booking/services';
            return;
        }
        if (!state.start_ts) {
            window.location.href = '/booking/time';
            return;
        }

        const comment = document.getElementById('comment');
        const promo = document.getElementById('promo');
        const nextBtn = document.getElementById('next-btn');

        if (comment) comment.value = state.comment || '';
        if (promo) promo.value = state.promo_code || '';

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                patchState({
                    comment: comment ? comment.value.trim() : '',
                    promo_code: promo ? promo.value.trim() : '',
                });
                window.location.href = '/booking/confirm';
            });
        }
    }

    async function initConfirmPage() {
        mustBeInTelegram();
        await ensureUser();

        const ok = await hasForm().catch(() => false);
        if (!ok) {
            showModal('form-required-modal');
            return;
        }

        const state = getState();
        if (!Array.isArray(state.service_ids) || !state.service_ids.length) {
            window.location.href = '/booking/services';
            return;
        }
        if (!state.start_ts) {
            window.location.href = '/booking/time';
            return;
        }

        const isReschedule = Boolean(state.booking_id);

        const root = document.getElementById('confirm-root');
        const submitBtn = document.getElementById('submit-btn');
        const errEl = document.getElementById('error');
        const dtEl = document.getElementById('dt');

        if (submitBtn) submitBtn.textContent = isReschedule ? 'Подтвердить перенос' : 'Подтвердить запись';
        if (dtEl) dtEl.textContent = formatDateTime(state.start_ts);

        const data = await api('/api/booking/services');
        const services = Array.isArray(data && data.services) ? data.services : [];
        const byId = new Map(services.map((s) => [Number(s.id), s]));
        const chosen = state.service_ids.map((id) => byId.get(Number(id))).filter(Boolean);

        const totalPrice = chosen.reduce((acc, s) => acc + Number(s.price || 0), 0);
        const totalMin = chosen.reduce((acc, s) => acc + Number(s.duration_min || 0), 0);

        if (root) {
            root.innerHTML = `
                <div class="confirm-row">
                    <div class="muted">Специалист</div>
                    <div><strong>${escapeHtml(document.body.dataset.specialist || '')}</strong></div>
                </div>
                <div class="confirm-row">
                    <div class="muted">Дата и время</div>
                    <div><strong>${escapeHtml(formatDateTime(state.start_ts))}</strong></div>
                </div>
                <div class="confirm-row">
                    <div class="muted">Услуги</div>
                    <div class="confirm-services">
                        ${chosen
                            .map(
                                (s) =>
                                    `<div>• ${escapeHtml(s.name)} <span class="muted">(${minutesLabel(s.duration_min)}, ${money(s.price)})</span></div>`
                            )
                            .join('')}
                    </div>
                </div>
                <div class="confirm-row">
                    <div class="muted">Итого</div>
                    <div><strong>${minutesLabel(totalMin)} • ${money(totalPrice)}</strong></div>
                </div>
                <div class="confirm-row">
                    <div class="muted">Комментарий</div>
                    <div>${escapeHtml(state.comment || '—')}</div>
                </div>
                <div class="confirm-row">
                    <div class="muted">Промокод</div>
                    <div>${state.promo_code ? `<code>${escapeHtml(state.promo_code)}</code>` : '—'}</div>
                </div>
            `;
        }

        function setError(msg) {
            if (!errEl) return;
            errEl.textContent = msg || '';
            if (msg) errEl.classList.add('is-visible');
            else errEl.classList.remove('is-visible');
        }

        if (submitBtn) {
            submitBtn.addEventListener('click', async () => {
                setError('');
                submitBtn.disabled = true;
                submitBtn.textContent = isReschedule ? 'Переносим…' : 'Сохраняем…';

                try {
                    const initData = getInitData();
                    if (!initData) throw new Error('tg_required');

                    const endpoint = isReschedule ? '/api/booking/reschedule' : '/api/booking/create';
                    const result = await api(endpoint, {
                        method: 'POST',
                        body: JSON.stringify({
                            initData,
                            booking: {
                                id: state.booking_id || null,
                                service_ids: state.service_ids,
                                start_ts: state.start_ts,
                                comment: state.comment || null,
                                promo_code: state.promo_code || null,
                            },
                        }),
                    });

                    const id = result && result.booking ? result.booking.id : null;
                    clearState();
                    window.location.href = id ? `/booking/success?id=${encodeURIComponent(id)}` : '/booking/success';
                } catch (e) {
                    const code = (e && e.payload && e.payload.error) || e.message || 'Ошибка';
                    setError(mapError(code));
                    submitBtn.disabled = false;
                    submitBtn.textContent = isReschedule ? 'Подтвердить перенос' : 'Подтвердить запись';
                }
            });
        }
    }

    async function initSuccessPage() {
        mustBeInTelegram();
        await ensureUser();

        const idEl = document.getElementById('booking-id');
        const qs = new URLSearchParams(window.location.search);
        const id = qs.get('id');
        if (idEl) idEl.textContent = id ? `№ ${id}` : '';

        const btn = document.getElementById('to-client');
        if (btn) btn.addEventListener('click', () => (window.location.href = '/client'));

        const again = document.getElementById('to-booking');
        if (again) again.addEventListener('click', () => (window.location.href = '/booking'));
    }

    async function initClientPage() {
        mustBeInTelegram();
        await ensureUser();

        const uid = getUserId();
        if (!uid) return;

        const has = await hasForm().catch(() => false);
        if (!has) {
            showModal('form-required-modal');
            return;
        }

        const profileRoot = document.getElementById('client-profile');
        const upcomingRoot = document.getElementById('upcoming');
        const pastRoot = document.getElementById('past');

        const p = await api(`/api/profile/details/${encodeURIComponent(uid)}`);
        if (p && p.profile && profileRoot) {
            profileRoot.innerHTML = `
                <div class="client-row"><div class="muted">Имя</div><div><strong>${escapeHtml(p.profile.full_name || '—')}</strong></div></div>
                <div class="client-row"><div class="muted">Телефон</div><div>${escapeHtml(p.profile.phone_number || '—')}</div></div>
                <div class="client-row"><div class="muted">Дата рождения</div><div>${escapeHtml(p.profile.birth_date || '—')}</div></div>
            `;
        }

        async function load() {
            const up = await api(`/api/booking/list/${encodeURIComponent(uid)}?kind=upcoming`);
            const past = await api(`/api/booking/list/${encodeURIComponent(uid)}?kind=past`);

            const upcomingItems = Array.isArray(up && up.items) ? up.items : [];
            const pastItems = Array.isArray(past && past.items) ? past.items : [];

            if (upcomingRoot) upcomingRoot.innerHTML = renderBookings(upcomingItems, true);
            if (pastRoot) pastRoot.innerHTML = renderBookings(pastItems, false);

            const byId = new Map(upcomingItems.map((b) => [String(b.id), b]));

            const cancelBtns = document.querySelectorAll('[data-cancel-booking]');
            cancelBtns.forEach((btn) => {
                btn.addEventListener('click', async () => {
                    const id = btn.getAttribute('data-cancel-booking');
                    if (!id) return;

                    const ok = await tgConfirm('Отменить запись?');
                    if (!ok) return;

                    const initData = getInitData();
                    if (!initData) return;

                    btn.disabled = true;
                    try {
                        await api('/api/booking/cancel', {
                            method: 'POST',
                            body: JSON.stringify({ initData, booking_id: Number(id) }),
                        });
                        await load();
                    } catch (e) {
                        btn.disabled = false;
                        const msg = mapError((e && e.payload && e.payload.error) || e.message || 'request_failed');
                        if (tg && typeof tg.showPopup === 'function') {
                            try {
                                tg.showPopup({ title: 'Ошибка', message: msg, buttons: [{ type: 'close', text: 'ОК' }] });
                            } catch (err) {
                                alert(msg);
                            }
                        } else {
                            alert(msg);
                        }
                    }
                });
            });

            const rescheduleBtns = document.querySelectorAll('[data-reschedule-booking]');
            rescheduleBtns.forEach((btn) => {
                btn.addEventListener('click', () => {
                    const id = btn.getAttribute('data-reschedule-booking');
                    if (!id) return;
                    const b = byId.get(String(id));
                    if (!b) return;

                    const services = Array.isArray(b.services) ? b.services : [];
                    const serviceIds = services.map((s) => Number(s.id)).filter((x) => Number.isFinite(x));

                    clearState();
                    patchState({
                        booking_id: Number(id),
                        service_ids: serviceIds,
                        start_ts: null,
                        comment: b.comment || '',
                        promo_code: b.promo_code || '',
                    });
                    window.location.href = '/booking/time';
                });
            });
        }

        await load();
    }

    function renderBookings(items, withActions) {
        if (!items || !items.length) return '<div class="empty">Пока нет записей</div>';
        return `
            <div class="booking-list">
                ${items
                    .map((b) => {
                        const dtLabel = formatDateTime(b.start_ts);
                        const services = Array.isArray(b.services) ? b.services : [];
                        const title = services.length ? services.map((s) => s.name).join(', ') : 'Услуга';
                        const price = b.total_price != null ? money(b.total_price) : '—';
                        const actions = withActions
                            ? `
                                <div class="booking-actions">
                                    <button class="btn btn-small" type="button" data-reschedule-booking="${escapeHtml(b.id)}">🔁 Перенести</button>
                                    <button class="btn btn-small btn-danger" type="button" data-cancel-booking="${escapeHtml(b.id)}">✖ Отменить</button>
                                </div>
                            `
                            : '';

                        return `
                            <div class="booking-item">
                                <div class="booking-top">
                                    <strong>${escapeHtml(title)}</strong>
                                    <span class="muted">${escapeHtml(price)}</span>
                                </div>
                                <div class="booking-sub">
                                    <span>🕒 ${escapeHtml(dtLabel)}</span>
                                </div>
                                ${actions}
                            </div>
                        `;
                    })
                    .join('')}
            </div>
        `;
    }

    function mapError(code) {
        const m = {
            form_required: 'Перед записью нужно заполнить анкету.',
            services_required: 'Выберите услугу.',
            start_ts_required: 'Выберите время.',
            start_ts_invalid: 'Некорректное время.',
            slot_unavailable: 'Это время уже заняли. Выберите другой слот.',
            outside_working_hours: 'Время вне графика работы.',
            booking_not_found: 'Запись не найдена.',
            booking_not_allowed: 'Нельзя изменить эту запись.',
            tg_required: 'Откройте запись внутри Telegram.',
            telegram_user_missing: 'Откройте запись внутри Telegram.',
            booking_id_invalid: 'Некорректный идентификатор записи.',
        };
        return m[code] || 'Не удалось выполнить действие. Попробуйте ещё раз.';
    }

    async function bootstrap() {
        if (tg) {
            tg.ready();
            tg.expand();
            try {
                tg.enableClosingConfirmation();
            } catch (e) {
                // ignore
            }
        }

        const page = document.body && document.body.dataset ? document.body.dataset.page : null;
        if (page === 'booking-profile') return initProfilePage();
        if (page === 'booking-services') return initServicesPage();
        if (page === 'booking-time') return initTimePage();
        if (page === 'booking-comment') return initCommentPage();
        if (page === 'booking-confirm') return initConfirmPage();
        if (page === 'booking-success') return initSuccessPage();
        if (page === 'client-profile') return initClientPage();
    }

    document.addEventListener('DOMContentLoaded', () => {
        bootstrap().catch((e) => console.error(e));
    });
})();
