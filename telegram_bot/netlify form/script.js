window.onload = function() {
    Telegram.WebApp.MainButton.text = "Отправить";
    Telegram.WebApp.MainButton.show()

    Telegram.WebApp.MainButton.onClick(submitForm);
}

var allPetIndex = 1;

function parseFormToJson() {
    const fullName = document.querySelector('input[name="full_name"]').value;
    const phoneNumber = document.querySelector('input[name="phone_number"]').value;
    const humanBirthDate = document.querySelector('input[name="birth_date"]').value;
    const aboutMe = document.querySelector('textarea[name="about_me"]').value;

    const pets = [];

    const petEntries = document.querySelectorAll('.pet_entry');

    petEntries.forEach(petEntry => {
        const petName = petEntry.querySelector('input[name="name"]').value;
        const petWeight = parseInt(petEntry.querySelector('input[name="weight"]').value);
        const petBirthDate = petEntry.querySelector('input[name="birth_date"]').value;
        const petBreed = petEntry.querySelector('input[name="breed"]').value;
        const petType = petEntry.querySelector('input[name^="pet_type"]:checked').value;
        const petGender = petEntry.querySelector('input[name^="gender"]:checked').value;

        const pet = {
            name: petName,
            weight: petWeight,
            birth_date: petBirthDate,
            breed: petBreed,
            gender: petGender,
            type: petType
        };

        pets.push(pet);
    });

    const jsonData = {
        pets: pets,
        human: {
            full_name: fullName,
            birth_date: humanBirthDate,
            phone_number: phoneNumber,
            about_me: aboutMe
        }
    };

    const jsonString = JSON.stringify(jsonData, null, 2);

    return [jsonData, jsonString];
}

function submitForm() {
    const form = document.getElementById("form_body");
    if (form.checkValidity()) {
        const jsonDataList = parseFormToJson();
        const jsonString = jsonDataList[1];
        const jsonData = jsonDataList[0];
        Telegram.WebApp.sendData(jsonString);
    } else {
        const petEntries = document.querySelectorAll('.pet_entry');
        petEntries.forEach(petEntry => {
            const inputs = petEntry.querySelectorAll('input');
            let isValid = true;
            inputs.forEach(input => {
                if (!input.checkValidity()) {
                    isValid = false;
                }
            });
            if (!isValid) {
                petEntry.style.maxHeight = null;
                petEntry.querySelector('.arrow_down svg').style.rotate = null;
                petEntry.querySelector('.trashcan svg').style.scale = null;
            }
        });
        form.reportValidity();
    }
}

function formatPhoneNumber(input) {
    let digits = input.value.replace(/(?!^\+)\D/g, '');

    if (digits.length > 12) {
        digits = digits.substring(0, 12);
    }

    let formatted = '+7';
    if (digits.length > 2) {
        formatted += ' (' + digits.substring(2, 5);
    }
    if (digits.length > 5) {
        formatted += ') ' + digits.substring(5, 8);
    }
    if (digits.length > 8) {
        formatted += '-' + digits.substring(8, 10);
    }
    if (digits.length > 10) {
        formatted += '-' + digits.substring(10, 12);
    }

    input.value = formatted;
}

function validateAndCapitalize(input) {
    value = input.value

    value = value
        .split(/\s+/)
        .map(word => word.charAt(0).toUpperCase() + word.slice(1, 15).toLowerCase())
        .join(' ');

    if (value.endsWith(" ") && value.split(/\s+/).length == 4) {
        value = value.trim();
    }

    input.value = value;

    const regex = /^([А-Я][а-я]{1,15}\s){2}[А-Я][а-я]{1,}$/;
    if (!regex.test(input.value)) {
        console.log("Invalid input. Ensure exactly three words, each starting with a capital letter and having at least 2 characters.");
    } else {
        console.log("Valid input:", input.value);
    }
}

function validateBreed(input) {
    const regex = /^[А-Яа-яA-Za-z\s]+$/;
    if (!regex.test(input.value)) {
        input.setCustomValidity("Порода не должна содержать цифры или специальные символы.");
    } else {
        input.setCustomValidity("");
    }
}

function addPet(button) {
    var pets_entries = document.getElementById("pets_entries");
    var user_pets = document.getElementsByClassName("pet_entry");
    if (user_pets.length == 49) {
        button.disabled = true
    }
    if (user_pets.length < 50) {
        allPetIndex += 1;
        var petIndex = user_pets.length + 1;
        el = document.createElement("div");
        el.classList.add("pet_entry");
        el.innerHTML = `
        <span>
            <label class="pet_top_label">Питомец ${petIndex}</label>
            <div class="arrow_down" onclick="">
                <svg onclick="hidePet(this);" style="position: absolute; top: 5px; right: 5px; transition: ease 0.2s;" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="6 9 12 15 18 9"/>
                </svg>
            </div>
        </span>
        <div class="entry" style="margin-top: 22px;">
            <label for="name">Кличка</label>
            <span class="input_container"><input name="name" maxlength="32" oninput="this.value = this.value.charAt(0).toUpperCase() + this.value.slice(1).trim();" required>
            <span></span></span>
        </div>
        <div class="entry">
            <label for="weight">Примерный вес (кг.)</label>
            <span class="input_container"><input name="weight" type="number" min="0" max="100" required>
            <span></span></span>
        </div>
        <div class="entry">
            <label for="birth_date">Дата рождения</label>
            <span class="input_container"><input name="birth_date" type="date" min="1900-01-01" onfocus="this.setAttribute('max', new Date().toISOString().slice(0, 10))" required>
            <span></span></span>
        </div>
        <div class="entry">
            <label for="breed">Порода</label>
            <span class="input_container"><input name="breed" maxlength="32" oninput="validateBreed(this)" required>
            <span></span></span>
        </div>
        <div class="entry">
            <label for="gender">Пол</label>
            <span class="input_container">
                <input name="gender_${allPetIndex}" type="radio" value="male" required>
                <label for="gender_${allPetIndex}">Мужской</label>
            </span>
            <span class="input_container" style="margin-top: 5px;">
                <input name="gender_${allPetIndex}" type="radio" value="female" required>
                <label for="gender_${allPetIndex}">Женский</label>
            </span>
        </div>
        <div class="entry">
            <label for="pet_type">Вид питомца</label>
            <span class="input_container">
                <input name="pet_type_${allPetIndex}" type="radio" value="dog" required>
                <label for="pet_type_${allPetIndex}">Собака</label>
            </span>
            <span class="input_container" style="margin-top: 5px;">
                <input name="pet_type_${allPetIndex}" type="radio" value="cat" required>
                <label for="pet_type_${allPetIndex}">Кот</label>
            </span>
        </div>
        <div class="trashcan" onclick="removePet(this);">
            <svg onmousedown="this.style.scale = 0.8" onmouseleave="this.style.scale = 1" onmouseup="this.style.scale = 1" style="position: absolute; bottom: 5px; right: 5px; transition: ease 0.2s;" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
        </div>`;
        pets_entries.appendChild(el);
        window.scrollTo(0, parseInt(window.getComputedStyle(document.getElementById("form_body")).height));
    }
}

function hidePet(button) {
    pete = button.parentElement.parentElement.parentElement; 
    if (button.style.rotate == '-180deg') {
        pete.style.maxHeight = null; 
        button.style.rotate = null; 
        pete.querySelector('.trashcan').querySelector("svg").style.scale = null;
    } else {
        button.style.rotate = '-180deg'; 
        pete.style.maxHeight = '12px';
        pete.querySelector('.trashcan').querySelector("svg").style.scale = 0;
        // pete.getElementsByClassName('trashcan')[0].style.bottom = '-100px';
    }
}
function removePet(button) {
    var user_pets = document.getElementsByClassName("pet_entry");
    var pet_entry = button.parentElement;
    if (user_pets.length > 1) {
        pet_entry.style.scale = 0.5;
        setTimeout(() => {
            pet_entry.remove();
        }, 200);
    }
    if (user_pets.length < 50) {
        document.getElementById("add_pet_button").disabled = false;
    }
}