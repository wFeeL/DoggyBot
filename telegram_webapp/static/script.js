window.onload = async function() {
    const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
    if (!tg) {
        console.warn('Telegram WebApp API not available');
        // Страница анкеты рассчитана на Telegram Mini App.
        return;
    }
    tg.expand();
    tg.MainButton.text = "Сохранить";
    tg.MainButton.show();
    tg.ready();
    tg.MainButton.onClick(submitForm);

    const userData = await loadUserData();
    fillForm(userData);

    setMaxDates();
};

let allPetIndex = 1;
window.submitForm = submitForm;
window.addPet = addPet;
window.removePet = removePet;

function setMaxDates() {
    const today = new Date().toLocaleDateString('en-CA');

    document.querySelectorAll('input[type="date"]').forEach(input => {
        input.setAttribute('max', today);
    });
}

async function loadUserData() {
    const userId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
    if (!userId) return null;

    try {
        const initData = window.Telegram?.WebApp?.initData || '';
        const response = await fetch(`/get_user_data/${userId}`, {
            headers: initData ? { 'X-Tg-Init-Data': initData } : {},
        });
        return await response.json()
    } catch (error) {
        console.error("Ошибка загрузки данных:", error);
        return null;
    }
}

function addPetFromData(pet, index) {
    addPet();

    const petEntries = document.querySelectorAll("#pets_entries .pet_entry");
    const petEntry = petEntries[petEntries.length - 1];

    if (!petEntry) return;

    petEntry.querySelector('input[name="name"]').value = pet.name || "";
    petEntry.querySelector('input[name="weight"]').value = pet.approx_weight || "";
    petEntry.querySelector('input[name="birth_date"]').value = pet.birth_date || "";
    petEntry.querySelector('input[name="breed"]').value = pet.breed || "";
    const aboutPetField = petEntry.querySelector('textarea[name="about_pet"]');
    if (aboutPetField) {
        aboutPetField.value = pet.about_pet || "";
    }

    if (pet.gender) {
        const genderInput = petEntry.querySelector(`input[name^="gender_${allPetIndex}"][value="${pet.gender}"]`);
        if (genderInput) genderInput.checked = true;
    }

    if (pet.type) {
        const typeInput = petEntry.querySelector(`input[name^="pet_type_${allPetIndex}"][value="${pet.type}"]`);
        if (typeInput) typeInput.checked = true;
    }
}

function parseFormToJson(user_id) {
    const fullName = document.querySelector('input[name="full_name"]').value;
    const phoneNumber = document.querySelector('input[name="phone_number"]').value;
    const humanBirthDate = document.querySelector('input[name="birth_date"]').value;

    const pets = [];
    document.querySelectorAll('.pet_entry').forEach(petEntry => {
        const petName = petEntry.querySelector('input[name="name"]').value;
        const petWeightRaw = petEntry.querySelector('input[name="weight"]').value;
        const petWeight = petWeightRaw ? parseFloat(petWeightRaw) : null;
        const petBirthDate = petEntry.querySelector('input[name="birth_date"]').value || null;
        const petBreed = petEntry.querySelector('input[name="breed"]').value || "";
        const petType = petEntry.querySelector(`input[name^="pet_type"]:checked`)?.value;
        const petGender = petEntry.querySelector(`input[name^="gender"]:checked`)?.value;
        const petAbout = petEntry.querySelector('textarea[name="about_pet"]')?.value || "";

        if (petName) {
            pets.push({
                name: petName,
                weight: petWeight,
                birth_date: petBirthDate,
                breed: petBreed,
                gender: petGender,
                type: petType,
                about_pet: petAbout
            });
        }
    });

    return {
        pets: pets,
        human: {
            full_name: fullName,
            birth_date: humanBirthDate || null,
            phone_number: phoneNumber,
            user_id: user_id
        }
    };
}

function submitForm() {
    const petCount = document.querySelectorAll('.pet_entry').length;
    if (petCount === 0) {
        alert("Добавьте хотя бы одного питомца!");
        return;
    }
    const form = document.getElementById("form_body");
    if (form.checkValidity()) {
        const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
        if (!tg || !tg.initDataUnsafe?.user?.id) {
            alert('Откройте анкету внутри Telegram.');
            return;
        }
        const jsonData = parseFormToJson(tg.initDataUnsafe.user.id);
        const initData = tg.initData;

        fetch('/webapp_data', {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(initData ? { 'X-Tg-Init-Data': initData } : {})
            },
            body: JSON.stringify({
                initData: initData,
                formData: jsonData
            })
        })
        .then(response => response.json())
        .catch(error => {
            console.error("Ошибка запроса:", error);
            alert("Ошибка при отправке данных.");
        });
        (window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp.close() : null);
    } else {
        form.reportValidity();
    }
}

function formatPhoneNumber(input) {
    let value = input.value.replace(/\D/g, '');

    if (value.startsWith('8')) {
        value = '7' + value.slice(1);
    } else if (!value.startsWith('7')) {
        value = '7' + value;
    }

    if (value.length > 11) {
        value = value.slice(0, 11);
    }

    let formatted = '+7';
    if (value.length > 1) formatted += ' ' + value.slice(1, 4);
    if (value.length > 4) formatted += ' ' + value.slice(4, 7);
    if (value.length > 7) formatted += ' ' + value.slice(7, 9);
    if (value.length > 9) formatted += ' ' + value.slice(9, 11);

    input.value = formatted;

    if (value.length !== 11) {
        input.setCustomValidity("Введите правильный номер (+7 ХХХ ХХХ ХХ ХХ)");
    } else {
        input.setCustomValidity("");
    }
}

function validateBreed(input) {
    const regex = /^[А-Яа-яA-Za-z\s]+$/;
    if (!input.value) {
        input.setCustomValidity("");
        return;
    }
    input.setCustomValidity(regex.test(input.value) ? "" : "Порода не должна содержать цифры или спец. символы.");
}

function addPet() {
    const pets_entries = document.getElementById("pets_entries");
    const user_pets = document.getElementsByClassName("pet_entry");

    if (user_pets.length >= 50) {
        document.getElementById("add_pet_button").disabled = true;
        return;
    }

    allPetIndex++;
    const petIndex = user_pets.length + 1;
    const el = document.createElement("div");
    el.classList.add("pet_entry");

    el.innerHTML = `
        <div class="pet_header">
            <div class="pet_header_content">
                <span class="pet_top_label">Питомец ${petIndex}</span>
                <div class="pet_controls">
                    <div class="arrow_down" onclick="togglePet(this)">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="6 9 12 15 18 9"/>
                        </svg>
                    </div>
                    <div class="trashcan" onclick="removePet(this);">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </div>
                </div>
            </div>
        </div>
        <div class="pet_content">
            <div class="entry" style="margin-top: 15px;">
                <label for="name">Кличка *</label>
                <div class="input_container">
                    <input name="name" maxlength="32" required>
                    <span class="validation-icon"></span>
                </div>
            </div>
            <div class="entry">
                <label for="weight">Примерный вес (кг.)</label>
                <div class="input_container">
                    <input name="weight" type="number" min="0" max="100" step="0.1">
                    <span class="validation-icon"></span>
                </div>
            </div>
            <div class="entry">
                <label for="pet_birth_date">Дата рождения</label>
                <div class="input_container">
                    <input name="birth_date" type="date" min="1900-01-01">
                    <span class="validation-icon date-icon"></span>
                </div>
            </div>
            <div class="entry">
                <label for="breed">Порода</label>
                <div class="input_container">
                    <input name="breed" maxlength="32" oninput="validateBreed(this)">
                    <span class="validation-icon"></span>
                </div>
            </div>
            <div class="entry">
                <label for="gender">Пол *</label>
                <div class="radio-group">
                    <label class="radio-option">
                        <input type="radio" name="gender_${allPetIndex}" value="male" required>
                        <span class="radio-custom"></span>
                        <span class="radio-label">Мужской</span>
                    </label>
                    <label class="radio-option">
                        <input type="radio" name="gender_${allPetIndex}" value="female" required>
                        <span class="radio-custom"></span>
                        <span class="radio-label">Женский</span>
                    </label>
                </div>
            </div>
            <div class="entry">
                <label for="pet_type">Вид питомца *</label>
                <div class="radio-group">
                    <label class="radio-option">
                        <input type="radio" name="pet_type_${allPetIndex}" value="dog" required>
                        <span class="radio-custom"></span>
                        <span class="radio-label">Собака</span>
                    </label>
                    <label class="radio-option">
                        <input type="radio" name="pet_type_${allPetIndex}" value="cat" required>
                        <span class="radio-custom"></span>
                        <span class="radio-label">Кот</span>
                    </label>
                </div>
            </div>
            <div class="entry">
                <label for="about_pet">О питомце (по желанию)</label>
                <div class="input_container">
                    <textarea name="about_pet" placeholder="Особенности поведения, отношение к другим животным, питание и всё важное." maxlength="2048"></textarea>
                    <span class="validation-icon"></span>
                </div>
            </div>
        </div>
    `;

    pets_entries.appendChild(el);

    setMaxDates();
}

function fillForm(data) {
    if (!data) return;
    document.querySelector('input[name="full_name"]').value = data.full_name || "";
    document.querySelector('input[name="phone_number"]').value = data.phone_number || "";
    document.querySelector('input[name="birth_date"]').value = data.birth_date || "";

    const petsContainer = document.getElementById("pets_entries");
    petsContainer.innerHTML = "";

    if (data.pets && data.pets.length > 0) {
        data.pets.forEach((pet, index) => addPetFromData(pet, index + 1));
    } else {
        // Добавить минимум одного питомца
        addPet();
    }
}

function togglePet(element) {
    const petEntry = element.closest('.pet_entry');
    const petContent = petEntry.querySelector('.pet_content');
    const arrow = element.querySelector('svg');

    petContent.classList.toggle('collapsed');

    if (petContent.classList.contains('collapsed')) {
        arrow.style.transform = 'rotate(180deg)';
    } else {
        arrow.style.transform = 'rotate(0deg)';
    }
}

function removePet(button) {
    if (document.querySelectorAll('.pet_entry').length <= 1) {
        alert("Должен остаться хотя бы один питомец!");
        return;
    }

    const petEntry = button.closest('.pet_entry');
    petEntry.remove();

    document.querySelectorAll('.pet_entry').forEach((entry, index) => {
        entry.querySelector('.pet_top_label').textContent = `Питомец ${index + 1}`;
    });
}
