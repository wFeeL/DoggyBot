window.onload = async function() {
    Telegram.WebApp.expand();
    Telegram.WebApp.MainButton.text = "Сохранить";
    Telegram.WebApp.MainButton.show();
    Telegram.WebApp.ready();
    Telegram.WebApp.MainButton.onClick(submitForm);

    console.log("Telegram Web App initialized");
    console.log("User data:", Telegram.WebApp.initDataUnsafe);
    console.log("Init data:", Telegram.WebApp.initData);

    const userData = await loadUserData();
    fillForm(userData);
};

let allPetIndex = 1;
window.submitForm = submitForm;
window.addPet = addPet;
window.removePet = removePet;
window.deletePet = deletePet;
window.togglePet = togglePet;

async function loadUserData() {
    const userId = window.Telegram.WebApp.initDataUnsafe.user?.id;

    try {
        const response = await fetch(`/get_user_data/${userId}`);
        return await response.json();
    } catch (error) {
        console.error("Ошибка загрузки данных:", error);
        return null;
    }
}

function fillForm(data) {
    console.log(data);
    if (data) {
        document.querySelector('input[name="full_name"]').value = data.full_name || "";
        document.querySelector('input[name="phone_number"]').value = data.phone_number || "";
        document.querySelector('input[name="birth_date"]').value = data.birth_date || "";
        document.querySelector('textarea[name="about_me"]').value = data.about_me || "";
    }

    const petsContainer = document.getElementById("pets_entries");
    petsContainer.innerHTML = "";

    if (data && data.pets && data.pets.length > 0) {
        // Очищаем allPetIndex и сбрасываем счетчик
        allPetIndex = 0;
        data.pets.forEach((pet, index) => {
            allPetIndex++;
            addPetFromData(pet, index + 1);
        });
    } else {
        // Если нет данных, оставляем первую карточку в DOM (она уже есть в HTML)
        allPetIndex = 1;
        // Первая карточка должна быть развернута
        const firstPet = document.querySelector('.pet_entry');
        if (firstPet) {
            firstPet.classList.remove('collapsed');
        }
    }
    updatePetNumbers();
}

function addPetFromData(pet, index) {
    const pets_entries = document.getElementById("pets_entries");
    const user_pets = document.getElementsByClassName("pet_entry");
    const petIndex = user_pets.length + 1;

    const el = document.createElement("div");
    el.classList.add("pet_entry", "card");

    // Если это первый питомец и он уже есть в DOM, обновляем его
    if (index === 1 && user_pets.length === 0) {
        // Обновляем существующую карточку
        const existingCard = document.querySelector('.pet_entry.card');
        if (existingCard) {
            fillPetCard(existingCard, pet, index);
            return;
        }
    }

    el.innerHTML = getPetCardHTML(petIndex, allPetIndex);
    pets_entries.appendChild(el);

    // Заполняем данные
    fillPetCard(el, pet, index);

    // Для всех питомцев кроме первого - сворачиваем
    if (index > 1) {
        el.classList.add('collapsed');
    }
}

function fillPetCard(card, pet, index) {
    if (!card) return;

    card.querySelector('input[name="name"]').value = pet.name || "";
    card.querySelector('input[name="weight"]').value = pet.approx_weight || pet.weight || "";
    card.querySelector('input[name="birth_date"]').value = pet.birth_date || "";
    card.querySelector('input[name="breed"]').value = pet.breed || "";

    if (pet.gender) {
        const genderInput = card.querySelector(`input[name^="gender_"][value="${pet.gender}"]`);
        if (genderInput) genderInput.checked = true;
    }

    if (pet.type) {
        const typeInput = card.querySelector(`input[name^="pet_type_"][value="${pet.type}"]`);
        if (typeInput) typeInput.checked = true;
    }
}

function getPetCardHTML(petIndex, genderTypeIndex) {
    return `
        <div class="pet_header" onclick="togglePet(this.parentElement)">
            <div class="pet_header_content">
                <span class="pet_top_label">Питомец ${petIndex}</span>
                <div class="pet_actions">
                    <button class="delete_pet" onclick="deletePet(this)" title="Удалить питомца">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            <line x1="10" y1="11" x2="10" y2="17"></line>
                            <line x1="14" y1="11" x2="14" y2="17"></line>
                        </svg>
                    </button>
                    <div class="arrow_down">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="6 9 12 15 18 9"/>
                        </svg>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="pet_content">
            <div class="entry">
                <label for="name">Кличка</label>
                <span class="input_container">
                    <input name="name" maxlength="32" oninput="this.value = this.value.charAt(0).toUpperCase() + this.value.slice(1).trim();" required>
                    <span></span>
                </span>
            </div>
            
            <div class="entry">
                <label for="weight">Примерный вес (кг.)</label>
                <span class="input_container">
                    <input name="weight" type="number" min="0" max="100" required>
                    <span></span>
                </span>
            </div>
            
            <div class="entry">
                <label for="birth_date">Дата рождения</label>
                <span class="input_container">
                    <input name="birth_date" type="date" min="1900-01-01" onfocus="this.setAttribute('max', new Date().toISOString().slice(0, 10))" required>
                    <span></span>
                </span>
            </div>
            
            <div class="entry">
                <label for="breed">Порода</label>
                <span class="input_container">
                    <input name="breed" maxlength="32" oninput="validateBreed(this)" required>
                    <span></span>
                </span>
            </div>
            
            <div class="entry">
                <label>Пол</label>
                <div class="radio-group">
                    <label class="radio-option">
                        <input type="radio" name="gender_${genderTypeIndex}" value="male" required>
                        <span class="radio-custom"></span>
                        <span class="radio-label">Мужской</span>
                    </label>
                    <label class="radio-option">
                        <input type="radio" name="gender_${genderTypeIndex}" value="female" required>
                        <span class="radio-custom"></span>
                        <span class="radio-label">Женский</span>
                    </label>
                </div>
            </div>
            
            <div class="entry">
                <label>Вид питомца</label>
                <div class="radio-group">
                    <label class="radio-option">
                        <input type="radio" name="pet_type_${genderTypeIndex}" value="dog" required>
                        <span class="radio-custom"></span>
                        <span class="radio-label">Собака</span>
                    </label>
                    <label class="radio-option">
                        <input type="radio" name="pet_type_${genderTypeIndex}" value="cat" required>
                        <span class="radio-custom"></span>
                        <span class="radio-label">Кот</span>
                    </label>
                </div>
            </div>
        </div>
    `;
}

function parseFormToJson(user_id) {
    const fullName = document.querySelector('input[name="full_name"]').value;
    const phoneNumber = document.querySelector('input[name="phone_number"]').value;
    const humanBirthDate = document.querySelector('input[name="birth_date"]').value;
    const aboutMe = document.querySelector('textarea[name="about_me"]').value;

    const pets = [];
    document.querySelectorAll('.pet_entry').forEach(petEntry => {
        const petName = petEntry.querySelector('input[name="name"]').value;
        const petWeight = parseInt(petEntry.querySelector('input[name="weight"]').value) || 0;
        const petBirthDate = petEntry.querySelector('input[name="birth_date"]').value;
        const petBreed = petEntry.querySelector('input[name="breed"]').value;
        const petType = petEntry.querySelector(`input[name^="pet_type"]:checked`)?.value;
        const petGender = petEntry.querySelector(`input[name^="gender"]:checked`)?.value;

        if (petName) {
            pets.push({
                name: petName,
                approx_weight: petWeight,
                birth_date: petBirthDate,
                breed: petBreed,
                gender: petGender,
                type: petType
            });
        }
    });

    return {
        pets: pets,
        human: {
            full_name: fullName,
            birth_date: humanBirthDate,
            phone_number: phoneNumber,
            about_me: aboutMe,
            user_id: user_id
        }
    };
}

function submitForm() {
    const form = document.getElementById("form_body");
    if (form.checkValidity()) {
        const jsonData = parseFormToJson(Telegram.WebApp.initDataUnsafe.user.id);
        const initData = Telegram.WebApp.initData;

        fetch('/webapp_data', {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                initData: initData,
                formData: jsonData
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log("Данные успешно отправлены:", data);
            Telegram.WebApp.close();
        })
        .catch(error => {
            console.error("Ошибка запроса:", error);
            alert("Ошибка при отправке данных.");
        });
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
    el.classList.add("pet_entry", "card");

    // Новая карточка добавляется развернутой
    el.innerHTML = getPetCardHTML(petIndex, allPetIndex);

    pets_entries.appendChild(el);

    // Фокус на первое поле
    setTimeout(() => {
        const firstInput = el.querySelector('input[name="name"]');
        if (firstInput) {
            firstInput.focus();
        }
    }, 100);

    updatePetNumbers();
}

function removePet(button) {
    const petCard = button.closest('.pet_entry');
    if (!petCard) return;

    const petCount = document.querySelectorAll('.pet_entry').length;
    if (petCount <= 1) {
        alert('Должен остаться хотя бы один питомец');
        return;
    }

    if (confirm('Удалить этого питомца?')) {
        petCard.remove();
        updatePetNumbers();
        allPetIndex--;
    }
}

function deletePet(button) {
    const petCard = button.closest('.pet_entry');
    if (!petCard) return;

    const petCount = document.querySelectorAll('.pet_entry').length;
    if (petCount <= 1) {
        alert('Должен остаться хотя бы один питомец');
        return;
    }

    if (confirm('Удалить этого питомца?')) {
        petCard.remove();
        updatePetNumbers();
    }
}

function togglePet(element) {
    // Получаем карточку, на которую кликнули
    let petCard;
    if (element.classList.contains('pet_header')) {
        petCard = element.parentElement;
    } else if (element.classList.contains('arrow_down')) {
        petCard = element.closest('.pet_entry');
    } else {
        petCard = element.closest('.pet_entry');
    }

    if (petCard) {
        petCard.classList.toggle('collapsed');
    }
}

function updatePetNumbers() {
    const petCards = document.querySelectorAll('.pet_entry');
    petCards.forEach((card, index) => {
        const label = card.querySelector('.pet_top_label');
        if (label) {
            label.textContent = `Питомец ${index + 1}`;
        }

        // Обновляем имена радио-кнопок
        const genderRadios = card.querySelectorAll('input[type="radio"][name^="gender_"]');
        if (genderRadios.length > 0) {
            const currentName = genderRadios[0].name;
            const baseName = currentName.replace(/_\d+$/, ''); // Убираем номер
            const newName = `${baseName}_${index + 1}`;
            genderRadios.forEach(radio => {
                radio.name = newName;
            });
        }

        const typeRadios = card.querySelectorAll('input[type="radio"][name^="pet_type_"]');
        if (typeRadios.length > 0) {
            const currentName = typeRadios[0].name;
            const baseName = currentName.replace(/_\d+$/, ''); // Убираем номер
            const newName = `${baseName}_${index + 1}`;
            typeRadios.forEach(radio => {
                radio.name = newName;
            });
        }
    });
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Убедимся, что первая карточка развернута
    const firstPet = document.querySelector('.pet_entry');
    if (firstPet) {
        firstPet.classList.remove('collapsed');
    }

    // Обновляем нумерацию питомцев
    updatePetNumbers();

    // Назначаем обработчики для всех заголовков карточек
    document.addEventListener('click', function(e) {
        if (e.target.closest('.pet_header')) {
            const petHeader = e.target.closest('.pet_header');
            const petCard = petHeader.parentElement;
            if (petCard) {
                petCard.classList.toggle('collapsed');
            }
        }
    });
});