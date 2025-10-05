window.onload = function() {
    Telegram.WebApp.expand();
    Telegram.WebApp.ready();
    // Скрываем кнопку "Сохранить" так как у нас своя кнопка
    Telegram.WebApp.MainButton.hide();
};

window.submitSurvey = submitSurvey;

function parseSurveyToJson(user_id) {
    const answers = {};

    // Собираем ответы на все вопросы
    for (let i = 1; i <= 5; i++) {
        const questionElement = document.querySelector(`textarea[name="question${i}"]`);
        if (questionElement) {
            answers[`question${i}`] = questionElement.value.trim();
        }
    }

    return {
        user_id: user_id,
        service_name: "Название услуги",
        answers: answers,
        timestamp: new Date().toISOString()
    };
}

function submitSurvey() {
    const form = document.getElementById("survey_form");

    if (form.checkValidity()) {
        const user_id = Telegram.WebApp.initDataUnsafe.user.id;
        const jsonData = parseSurveyToJson(user_id);
        const initData = Telegram.WebApp.initData;

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
        .then(response => response.json())
        .then(data => {
            if (data.ok) {
                Telegram.WebApp.showPopup({
                    title: "Успешно",
                    message: "Спасибо за ваши ответы!",
                    buttons: [{ type: "ok" }]
                });
            } else {
                throw new Error(data.error || "Произошла ошибка при отправке");
            }
        })
        .catch(error => {
            console.error("Ошибка запроса:", error);
            Telegram.WebApp.showPopup({
                title: "Ошибка",
                message: "Не удалось отправить данные. Попробуйте еще раз.",
                buttons: [{ type: "ok" }]
            });
        });
    } else {
        form.reportValidity();
    }
}

// Добавляем валидацию для textarea
document.addEventListener('DOMContentLoaded', function() {
    const textareas = document.querySelectorAll('textarea[name^="question"]');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            const span = this.parentElement.querySelector('span');
            if (this.value.trim().length > 0) {
                this.setCustomValidity("");
                span.style.display = 'inline';
            } else {
                this.setCustomValidity("Это поле обязательно для заполнения");
                span.style.display = 'inline';
            }
        });
    });
});