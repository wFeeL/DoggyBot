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
    const answers = {};

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
            return response.json();
        })
        .then(data => {
            console.log("Response data:", data);
            if (data.ok) {
                Telegram.WebApp.showPopup({
                    title: "Успешно",
                    message: "Спасибо за ваши ответы!",
                    buttons: [{ type: "ok" }]
                });
                // Очистка формы после успешной отправки
                form.reset();
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

// Добавляем валидацию для textarea
document.addEventListener('DOMContentLoaded', function() {
    const textareas = document.querySelectorAll('textarea[name^="question"]');
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