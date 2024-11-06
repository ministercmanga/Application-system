// Toggle between day and night mode
document.getElementById('modeSwitch').addEventListener('click', function () {
    const body = document.body;
    body.classList.toggle('dark-mode');
    
    const modeIcon = document.getElementById('modeSwitch').querySelector('i');
    if (body.classList.contains('dark-mode')) {
        modeIcon.classList.remove('fa-moon');
        modeIcon.classList.add('fa-sun');
        this.setAttribute('title', 'Switch to Day Mode');
    } else {
        modeIcon.classList.remove('fa-sun');
        modeIcon.classList.add('fa-moon');
        this.setAttribute('title', 'Switch to Night Mode');
    }
});

document.addEventListener('DOMContentLoaded', function () {
    const checkbox = document.getElementById('btn');
    const mainContent = document.querySelector('.main-content');

    checkbox.addEventListener('change', function () {
        if (checkbox.checked) {
            mainContent.classList.add('shifted');
        } else {
            mainContent.classList.remove('shifted');
        }
    });
});
    function generateMessage() {
        const statusSelect = document.getElementById('statusSelect');
        const messageBox = document.getElementById('statusMessage');
        const username = "{{ application.user.username }}";
        const course = "{{ application.course.name }}";
        let message = '';

        if (statusSelect.value === 'Approved') {
            message = `Congratulations ${username}, you have been conditionally accepted for ${course}.`;
        } else if (statusSelect.value === 'Declined') {
            message = `Dear ${username}, we regret to inform you that your application for ${course} has been declined.`;
        } else {
            message = '';
        }

        messageBox.value = message;
    }
    function communicateStatus(applicationId) {
        fetch(`/communicate_status/${applicationId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': '{{ csrf_token() }}'
            }
        }).then(response => response.json())
          .then(data => {
              if (data.success) {
                  location.reload();  // Reload to update the dashboard with the communication status
              } else {
                  alert('Failed to communicate the status.');
              }
          });
    }