window.onload = async function() {
    Telegram.WebApp.expand();
    Telegram.WebApp.MainButton.text = "Сохранить";
    Telegram.WebApp.MainButton.show();
    Telegram.WebApp.ready();
    Telegram.WebApp.MainButton.onClick(submitForm);

    try {
        const userData = await loadUserData();
        if (userData) {
            fillForm(userData);
        }
    } catch (error) {
        console.error("Ошибка загрузки данных пользователя:", error);
    }
};


let allPetIndex = 1;
window.submitForm = submitForm;
window.addPet = addPet;
window.removePet = removePet;

async function loadUserData() {
    const userId = window.Telegram.WebApp.initDataUnsafe.user.id;
    if (!userId) return null;

    try {
        const response = await fetch(`/get_user_data/${userId}`);
        return await response.json()
    } catch (error) {
        console.error("Ошибка загрузки данных:", error);
        return null;
    }
}

function fillForm(data) {
    console.log(data)
    document.querySelector('input[name="full_name"]').value = data.full_name || "";
    document.querySelector('input[name="phone_number"]').value = data.phone_number || "";
    document.querySelector('input[name="birth_date"]').value = data.birth_date || "";
    document.querySelector('textarea[name="about_me"]').value = data.about_me || "";

    const petsContainer = document.getElementById("pets_entries");
    petsContainer.innerHTML = "";
    if (data.pets && data.pets.length > 0) {
        data.pets.forEach((pet, index) => addPetFromData(pet, index + 1));
    }
}

function addPetFromData(pet, index) {
    addPet(); // Добавляем нового питомца

    // Получаем последний добавленный питомец
    const petEntries = document.querySelectorAll("#pets_entries .pet_entry");
    const petEntry = petEntries[petEntries.length - 1]; // Получаем последнего добавленного питомца

    if (!petEntry) return; // Защита от ошибок

    petEntry.querySelector('input[name="name"]').value = pet.name || "";
    petEntry.querySelector('input[name="weight"]').value = pet.approx_weight || "";
    petEntry.querySelector('input[name="birth_date"]').value = pet.birth_date || "";
    petEntry.querySelector('input[name="breed"]').value = pet.breed || "";

    // Проверяем существование элементов перед установкой `checked`
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
                weight: petWeight,
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

        fetch('https://doggyform.ru/webapp_data', {
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
        .catch(error => {
            console.error("Ошибка запроса:", error);
            alert("Ошибка при отправке данных.");
        });
        Telegram.WebApp.close();
    } else {
        form.reportValidity();
    }
}



function formatPhoneNumber(input) {
    let value = input.value.replace(/\D/g, '');

    if (value.startsWith('8')) {
        value = '7' + value.slice(1);  // Заменяем первую 8 на 7
    } else if (!value.startsWith('7')) {
        value = '7' + value;  // Добавляем 7 если нет
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
    el.classList.add("pet_entry");

    el.innerHTML = `
        <span>
            <label class="pet_top_label">Питомец ${petIndex}</label>
            <div class="arrow_down">
                <svg onclick="hidePet(this);" style="position: absolute; top: 5px; right: 5px; transition: ease 0.2s;" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="6 9 12 15 18 9"/>
                </svg>
            </div>
        </span>
        <div class="entry" style="margin-top: 22px;">
            <label for="name">Кличка</label>
            <input name="name" maxlength="32" required>
        </div>
        <div class="entry">
            <label for="weight">Примерный вес (кг.)</label>
            <input name="weight" type="number" min="0" max="100" required>
        </div>
        <div class="entry">
            <label for="birth_date">Дата рождения</label>
            <input name="birth_date" type="date" min="1900-01-01" required>
        </div>
        <div class="entry">
            <label for="breed">Порода</label>
            <input name="breed" maxlength="32" required>
        </div>
        <div class="entry">
            <label for="gender">Пол</label>
            <input name="gender_${allPetIndex}" type="radio" value="male" required> Мужской
            <input name="gender_${allPetIndex}" type="radio" value="female" required> Женский
        </div>
        <div class="entry">
            <label for="pet_type">Вид питомца</label>
            <input name="pet_type_${allPetIndex}" type="radio" value="dog" required> Собака
            <input name="pet_type_${allPetIndex}" type="radio" value="cat" required> Кот
        </div>
        <div class="trashcan" onclick="removePet(this);">
            <svg style="position: absolute; bottom: 5px; right: 5px;" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
        </div>
    `;

    pets_entries.appendChild(el);
}


function removePet(button) {
    button.parentElement.remove();
    allPetIndex--
}
