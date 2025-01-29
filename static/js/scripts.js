document.addEventListener('DOMContentLoaded', () => {
    const deleteForms = document.querySelectorAll('form[onsubmit]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const confirmed = confirm('Are you sure you want to delete this contact?');
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });

    const callForm = document.querySelector('form[action="/calls/add"]');
    if (callForm) {
        callForm.addEventListener('submit', (e) => {
            const phoneNr = document.getElementById('phone_nr').value;
            const phonePattern = /^\+?\d{10,15}$/;
            if (!phonePattern.test(phoneNr)) {
                alert('Please enter a valid phone number in the format +34655988111');
                e.preventDefault();
            }
        });
    }

    const contactForm = document.querySelector('form[action="/contacts/add"]');
    if (contactForm) {
        contactForm.addEventListener('submit', (e) => {
            const phoneNr = document.getElementById('phone_nr').value;
            const phonePattern = /^\+?\d{10,15}$/;
            if (!phonePattern.test(phoneNr)) {
                alert('Please enter a valid phone number in the format +34655988111');
                e.preventDefault();
            }
        });
    }

});