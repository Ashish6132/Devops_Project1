// College Complaint Management System

document.addEventListener("DOMContentLoaded", function () {
    console.log("Complaint Management System Loaded");

    // Form validation
    const forms = document.querySelectorAll("form");

    forms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const requiredFields =
                form.querySelectorAll("[required]");

            let isValid = true;

            requiredFields.forEach(function (field) {
                if (field.value.trim() === "") {
                    isValid = false;
                    field.style.borderColor = "red";
                } else {
                    field.style.borderColor = "#ccc";
                }
            });

            if (!isValid) {
                event.preventDefault();
                alert("Please fill in all required fields.");
            }
        });
    });
});