window.onload = function() {
    Telegram.WebApp.expand();
    Telegram.WebApp.ready();
    Telegram.WebApp.MainButton.hide();

    console.log("Telegram Web App initialized");
    console.log("User data:", Telegram.WebApp.initDataUnsafe);
    console.log("Init data:", Telegram.WebApp.initData);
};

window.submitSurvey = submitSurvey;

function parseSurveyToJson() {
    const user_id = Telegram.WebApp.initDataUnsafe.user?.id;
    const service_id = document.getElementById('service_id').value;
    const selected_option_text = document.getElementById('selected_option_text').value;
    const free_form = document.getElementById('free_form').value;

    return {
        user_id: user_id,
        service_id: parseInt(service_id),
        selected_option: selected_option_text,
        free_form: free_form
    };
}

function submitSurvey() {
    const form = document.getElementById("survey_form");

    // Проверяем, выбран ли вариант
    const selectedOption = document.querySelector('input[name="selected_option"]:checked');
    if (!selectedOption) {
        // Показываем красивое сообщение
        const firstCard = document.querySelector('.option-card');
        if (firstCard) {
            firstCard.style.borderColor = '#fc8181';
            firstCard.style.boxShadow = '0 0 0 3px rgba(252, 129, 129, 0.1)';

            setTimeout(() => {
                firstCard.style.borderColor = '';
                firstCard.style.boxShadow = '';
            }, 2000);
        }

        if (window.Telegram && Telegram.WebApp) {
            Telegram.WebApp.showPopup({
                title: "Внимание",
                message: "Пожалуйста, выберите один из вариантов услуги.",
                buttons: [{ type: "ok" }]
            });
        } else {
            alert("Пожалуйста, выберите один из вариантов услуги.");
        }
        return;
    }

    if (form.checkValidity()) {
        const jsonData = parseSurveyToJson();
        const initData = Telegram.WebApp.initData;

        console.log("Submitting data:", jsonData);
        console.log("Init data:", initData);
        console.log("Init data type:", typeof initData);

        // Проверяем initData
        if (!initData || typeof initData !== 'string') {
            if (window.Telegram && Telegram.WebApp) {
                Telegram.WebApp.showPopup({
                    title: "Ошибка",
                    message: "Ошибка инициализации приложения. Пожалуйста, перезагрузите страницу.",
                    buttons: [{ type: "ok" }]
                });
            } else {
                alert("Ошибка инициализации приложения. Пожалуйста, перезагрузите страницу.");
            }
            return;
        }

        // Показываем индикатор загрузки на кнопке
        const submitButton = document.querySelector('.submit-button');
        const originalText = submitButton.textContent;
        submitButton.textContent = 'Отправка...';
        submitButton.disabled = true;

        fetch('/survey_data', {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                initData: initData,
                surveyData: jsonData
            })
        })
        .then(response => {
            console.log("Response status:", response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Response data:", data);
            if (data.ok) {
                // Показываем успешное сообщение
                if (window.Telegram && Telegram.WebApp) {
                    Telegram.WebApp.showPopup({
                        title: "Успешно!",
                        message: "Спасибо за вашу заявку! Мы свяжемся с вами в ближайшее время.",
                        buttons: [{ type: "ok" }]
                    });

                    // Закрываем Web App через 2 секунды
                    setTimeout(() => {
                        Telegram.WebApp.close();
                    }, 2000);
                } else {
                    alert("Спасибо за вашу заявку! Мы свяжемся с вами в ближайшее время.");

                    // Очищаем форму
                    form.reset();
                    document.querySelectorAll('.option-card').forEach(card => {
                        card.classList.remove('selected');
                    });
                    document.getElementById('selected_option_text').value = '';

                    // Восстанавливаем кнопку
                    submitButton.textContent = 'Заявка отправлена! ✓';
                    setTimeout(() => {
                        submitButton.textContent = originalText;
                        submitButton.disabled = false;
                    }, 2000);
                }
            } else {
                throw new Error(data.error || "Произошла ошибка при отправке");
            }
        })
        .catch(error => {
            console.error("Ошибка запроса:", error);

            // Восстанавливаем кнопку
            submitButton.textContent = originalText;
            submitButton.disabled = false;

            // Показываем сообщение об ошибке
            if (window.Telegram && Telegram.WebApp) {
                Telegram.WebApp.showPopup({
                    title: "Ошибка",
                    message: `Не удалось отправить данные: ${error.message}`,
                    buttons: [{ type: "ok" }]
                });
            } else {
                alert(`Не удалось отправить данные: ${error.message}`);
            }
        });
    } else {
        form.reportValidity();
    }
}

// Добавляем валидацию для полей
document.addEventListener('DOMContentLoaded', function() {
    const textareas = document.querySelectorAll('textarea[name="free_form"]');

    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            if (this.value.trim().length > 0) {
                this.setCustomValidity("");
                this.style.borderColor = '#48bb78';
                this.style.backgroundColor = 'rgba(72, 187, 120, 0.05)';
            } else {
                this.setCustomValidity("Это поле обязательно для заполнения");
                this.style.borderColor = '#fc8181';
                this.style.backgroundColor = 'rgba(252, 129, 129, 0.05)';
            }
        });

        // Сброс стилей при фокусе
        textarea.addEventListener('focus', function() {
            this.style.borderColor = '#667eea';
            this.style.backgroundColor = 'white';
            this.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.1)';
        });

        textarea.addEventListener('blur', function() {
            if (this.value.trim().length > 0) {
                this.style.borderColor = '#48bb78';
                this.style.backgroundColor = 'rgba(72, 187, 120, 0.05)';
            } else {
                this.style.borderColor = '#e2e8f0';
                this.style.backgroundColor = '#f8fafc';
            }
            this.style.boxShadow = 'none';
        });
    });
});