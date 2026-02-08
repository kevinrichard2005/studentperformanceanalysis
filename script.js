document.addEventListener('DOMContentLoaded', function() {
    // Mobile Menu Toggle
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (navToggle) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    // Auto-hide Flash Messages
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 500);
        }, 5000);
    });

    // Dashboard Analytics (if chart containers exist)
    if (document.getElementById('subjectChart')) {
        fetch('/api/analytics')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    renderCharts(data);
                } else {
                    console.log('No data available for charts');
                }
            });
    }
});

function renderCharts(data) {
    // Subject-wise Performance Chart
    const ctxSubject = document.getElementById('subjectChart').getContext('2d');
    new Chart(ctxSubject, {
        type: 'bar',
        data: {
            labels: data.subjects,
            datasets: [{
                label: 'Average Marks',
                data: data.subject_averages,
                backgroundColor: 'rgba(79, 70, 229, 0.6)',
                borderColor: 'rgba(79, 70, 229, 1)',
                borderWidth: 1,
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, max: 100 }
            }
        }
    });

    // Marks Distribution Chart
    const ctxDist = document.getElementById('distributionChart').getContext('2d');
    new Chart(ctxDist, {
        type: 'doughnut',
        data: {
            labels: Object.keys(data.distribution),
            datasets: [{
                data: Object.values(data.distribution),
                backgroundColor: [
                    '#ef4444', // Fail
                    '#f59e0b', // Average
                    '#3b82f6', // Good
                    '#10b981'  // Excellent
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });

    // Attendance vs Marks Scatter Chart
    const ctxScatter = document.getElementById('scatterChart').getContext('2d');
    new Chart(ctxScatter, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Student Correlation',
                data: data.attendance_marks.map(item => ({ x: item.attendance, y: item.marks })),
                backgroundColor: 'rgba(79, 70, 229, 0.6)'
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: { title: { display: true, text: 'Attendance (%)' }, min: 0, max: 100 },
                y: { title: { display: true, text: 'Marks' }, min: 0, max: 100 }
            }
        }
    });
}
