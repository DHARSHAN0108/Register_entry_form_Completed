(function() {
  const dateInput = document.getElementById('id_appointment_date');
  const timeInput = document.getElementById('id_appointment_time');

  if (dateInput) {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    dateInput.min = `${yyyy}-${mm}-${dd}`;
  }

  function pad(n) { return String(n).padStart(2, '0'); }

  function updateTimeLimits(triggeredByUser = false) {
    if (!dateInput || !timeInput || !dateInput.value) return;

    const selectedDate = new Date(dateInput.value);
    const today = new Date();
    today.setHours(0,0,0,0);
    selectedDate.setHours(0,0,0,0);

    if (selectedDate.getTime() === today.getTime()) {
      const now = new Date();
      let hh = now.getHours();
      let min = now.getMinutes() + 1;
      if (min >= 60) { hh += 1; min = 0; }
      timeInput.min = `${pad(hh)}:${pad(min)}`;
      timeInput.max = "22:00";

      if (timeInput.value && timeInput.value < timeInput.min) {
        if (triggeredByUser) {
          document.getElementById('timeErrorMessage').innerText =
            "You cannot select a past time for today. Please choose a future time.";
          new bootstrap.Modal(document.getElementById('timeErrorModal')).show();
        }
        timeInput.value = "";
      }
    } else {
      timeInput.min = "09:00";
      timeInput.max = "22:00";

      if (timeInput.value && (timeInput.value < "09:00" || timeInput.value > "22:00")) {
        if (triggeredByUser) {
          document.getElementById('timeErrorMessage').innerText =
            "Appointments must be scheduled between 09:00 and 22:00.";
          new bootstrap.Modal(document.getElementById('timeErrorModal')).show();
        }
        timeInput.value = "";
      }
    }
  }

  if (dateInput) {
    dateInput.addEventListener('change', () => updateTimeLimits(false));
  }
  if (timeInput) {
    timeInput.addEventListener('focus', () => updateTimeLimits(false));
    timeInput.addEventListener('change', () => updateTimeLimits(true));
    timeInput.addEventListener('input', () => updateTimeLimits(true));
  }

  updateTimeLimits(false);
})();

// File validation
(function() {
  const fileInput = document.getElementById('documentInput') || document.getElementById('id_document');
  if (fileInput) {
    fileInput.addEventListener('change', function() {
      const file = this.files && this.files[0];
      if (file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
          document.getElementById('fileErrorMessage').innerText = "Only PDF files are allowed.";
          new bootstrap.Modal(document.getElementById('fileErrorModal')).show();
          this.value = "";
          return;
        }
        if (file.size > 2 * 1024 * 1024) {
          document.getElementById('fileErrorMessage').innerText = "File size must be less than 2MB.";
          new bootstrap.Modal(document.getElementById('fileErrorModal')).show();
          this.value = "";
        }
      }
    });
  }
})();
// document.querySelectorAll('.form-floating input, .form-floating select').forEach(input => {
//   input.addEventListener('input', function() {
//     const label = this.parentNode.querySelector('label');
//     if (this.value.trim() !== "") {
//       label.style.display = "none";  // Hide label once filled
//     } else {
//       label.style.display = "block"; // Show back if empty
//     }
//   });
// });
