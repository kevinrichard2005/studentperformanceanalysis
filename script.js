document.addEventListener('DOMContentLoaded', function () {
    // Mobile Menu Toggle
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            const icon = navToggle.querySelector('i');
            if (navLinks.classList.contains('active')) {
                icon.classList.replace('fa-bars', 'fa-times');
            } else {
                icon.classList.replace('fa-times', 'fa-bars');
            }
        });
    }

    // Auto-hide Flash Messages with Smooth Transition
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(flash => {
        // Initial timeout to start fade
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transform = 'translateX(20px)';
            // Wait for transition to finish before removing
            setTimeout(() => flash.remove(), 500);
        }, 5000);

        // Allow manual close on click
        flash.addEventListener('click', () => {
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 300);
        });
    });

    // Dashboard Analytics (if chart containers exist)
    const subjectCtx = document.getElementById('subjectChart');
    if (subjectCtx) {
        console.log('Dashboard detected, fetching analytics...');
        fetch('/api/analytics')
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                console.log('Analytics data received:', data);
                if (data.status === 'success') {
                    renderCharts(data);
                } else if (data.status === 'empty') {
                    console.log('No data available for charts');
                } else {
                    console.warn('Dashboard API returned status:', data.status);
                }
            })
            .catch(error => {
                console.error('Error loading analytics:', error);
            });
    }
});

function renderCharts(data) {
    const chartDefaults = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    font: { family: "'Inter', sans-serif", weight: '500' }
                }
            }
        }
    };

    // Subject-wise Performance Chart
    const ctxSubject = document.getElementById('subjectChart').getContext('2d');
    new Chart(ctxSubject, {
        type: 'bar',
        data: {
            labels: data.subjects,
            datasets: [{
                label: 'Average Marks',
                data: data.subject_averages,
                backgroundColor: 'rgba(30, 58, 138, 0.7)',
                borderColor: '#1e3a8a',
                borderWidth: 1,
                borderRadius: 8,
                hoverBackgroundColor: 'rgba(30, 58, 138, 0.9)'
            }]
        },
        options: {
            ...chartDefaults,
            plugins: { ...chartDefaults.plugins, legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: '#f1f5f9' },
                    ticks: { callback: value => value + '%' }
                },
                x: { grid: { display: false } }
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
                ],
                hoverOffset: 10,
                borderWidth: 0
            }]
        },
        options: {
            ...chartDefaults,
            cutout: '70%',
            plugins: {
                ...chartDefaults.plugins,
                legend: { position: 'bottom', labels: { padding: 20 } }
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
                backgroundColor: 'rgba(220, 38, 38, 0.6)',
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            ...chartDefaults,
            scales: {
                x: {
                    title: { display: true, text: 'Attendance (%)', font: { weight: '600' } },
                    min: 0,
                    max: 100,
                    grid: { color: '#f1f5f9' }
                },
                y: {
                    title: { display: true, text: 'Marks', font: { weight: '600' } },
                    min: 0,
                    max: 100,
                    grid: { color: '#f1f5f9' }
                }
            }
        }
    });
}
