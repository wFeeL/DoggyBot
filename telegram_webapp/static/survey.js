window.onload = function() {
    Telegram.WebApp.expand();
    Telegram.WebApp.ready();
    Telegram.WebApp.MainButton.hide();

    console.log("Telegram Web App initialized");
    console.log("User data:", Telegram.WebApp.initDataUnsafe);
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
        Telegram.WebApp.showPopup({
            title: "Внимание",
            message: "Пожалуйста, выберите один из вариантов услуги.",
            buttons: [{ type: "ok" }]
        });
        return;
    }

    if (form.checkValidity()) {
        const jsonData = parseSurveyToJson();
        const initData = Telegram.WebApp.initData;

        console.log("Submitting data:", jsonData);
        console.log("Init data available:", !!initData);

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
            return response.text();
        })
        .then(data => {
            console.log("Response data:", data);
            if (data.ok) {
                Telegram.WebApp.showPopup({
                    title: "Успешно",
                    message: "Спасибо за вашу заявку! Мы свяжемся с вами в ближайшее время.",
                    buttons: [{ type: "ok" }]
                });
                // Очистка формы после успешной отправки
                setTimeout(() => {
                    form.reset();
                    document.querySelectorAll('.option-card').forEach(card => {
                        card.classList.remove('selected');
                    });
                    document.querySelectorAll('.option-radio').forEach(radio => radio.checked = false);
                }, 1000);
            } else {
                throw new Error(data.error || "Произошла ошибка при отправке");
            }
        })
        .catch(error => {
            console.error("Ошибка запроса:", error);
            Telegram.WebApp.showPopup({
                title: "Ошибка",
                message: `Не удалось отправить данные: ${error.message}`,
                buttons: [{ type: "ok" }]
            });
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
            } else {
                this.setCustomValidity("Это поле обязательно для заполнения");
            }
        });
    });
});