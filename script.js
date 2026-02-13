/**
 * Student Portal - Main JavaScript
 * Version: 1.0.5
 */

document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // ========== MOBILE MENU TOGGLE ==========
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (navToggle && navLinks) {
        // Toggle menu
        navToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            navLinks.classList.toggle('active');
            
            const icon = navToggle.querySelector('i');
            if (icon) {
                if (navLinks.classList.contains('active')) {
                    icon.classList.remove('fa-bars');
                    icon.classList.add('fa-times');
                } else {
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            }
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            if (navLinks.classList.contains('active') && 
                !navToggle.contains(event.target) && 
                !navLinks.contains(event.target)) {
                navLinks.classList.remove('active');
                
                const icon = navToggle.querySelector('i');
                if (icon) {
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            }
        });

        // Close menu on window resize (if desktop)
        window.addEventListener('resize', function() {
            if (window.innerWidth > 768 && navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
                
                const icon = navToggle.querySelector('i');
                if (icon) {
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            }
        });
    }

    // ========== PASSWORD VISIBILITY TOGGLE ==========
    const togglePasswords = document.querySelectorAll('.toggle-password');
    togglePasswords.forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            const input = this.parentElement.querySelector('input');
            if (input) {
                const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
                input.setAttribute('type', type);
                this.classList.toggle('fa-eye');
                this.classList.toggle('fa-eye-slash');
            }
        });
    });

    // ========== FLASH MESSAGES ==========
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach((flash, index) => {
        // Stagger animation
        flash.style.animationDelay = `${index * 0.1}s`;

        // Auto-hide after 5 seconds
        const timeoutId = setTimeout(() => {
            hideFlashMessage(flash);
        }, 5000);

        // Manual close on click
        flash.addEventListener('click', () => {
            clearTimeout(timeoutId);
            hideFlashMessage(flash);
        });

        // Hover pause auto-hide
        flash.addEventListener('mouseenter', () => {
            clearTimeout(timeoutId);
        });

        flash.addEventListener('mouseleave', () => {
            setTimeout(() => {
                hideFlashMessage(flash);
            }, 2000);
        });
    });

    function hideFlashMessage(flash) {
        if (flash && flash.parentNode) {
            flash.style.opacity = '0';
            flash.style.transform = 'translateX(20px)';
            setTimeout(() => {
                if (flash.parentNode) {
                    flash.remove();
                }
            }, 300);
        }
    }

    // ========== DASHBOARD CHARTS ==========
    function initDashboardCharts() {
        const subjectCtx = document.getElementById('subjectChart');
        if (subjectCtx) {
            console.log('📊 Dashboard detected, fetching analytics...');
            
            // Show loading state
            showChartLoadingState();
            
            fetch('/api/analytics')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('📈 Analytics data received:', data);
                    
                    if (data.status === 'success' && data.subjects && data.subjects.length > 0) {
                        renderCharts(data);
                    } else if (data.status === 'empty') {
                        showEmptyChartState('No data available. Add student records to see analytics.');
                    } else {
                        showEmptyChartState('Unable to load chart data.');
                    }
                })
                .catch(error => {
                    console.error('❌ Error loading analytics:', error);
                    showEmptyChartState('Failed to load analytics. Please try again.');
                });
        }
    }

    function showChartLoadingState() {
        const charts = ['subjectChart', 'distributionChart', 'scatterChart'];
        charts.forEach(chartId => {
            const canvas = document.getElementById(chartId);
            if (canvas && canvas.parentNode) {
                canvas.style.opacity = '0.5';
                // Add loading spinner
                const parent = canvas.parentNode;
                if (!parent.querySelector('.chart-loading')) {
                    const loading = document.createElement('div');
                    loading.className = 'chart-loading text-muted';
                    loading.style.textAlign = 'center';
                    loading.style.padding = '2rem';
                    loading.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading charts...';
                    parent.style.position = 'relative';
                    parent.appendChild(loading);
                }
            }
        });
    }

    function showEmptyChartState(message) {
        const charts = ['subjectChart', 'distributionChart', 'scatterChart'];
        charts.forEach(chartId => {
            const canvas = document.getElementById(chartId);
            if (canvas && canvas.parentNode) {
                // Remove loading state if exists
                const loading = canvas.parentNode.querySelector('.chart-loading');
                if (loading) loading.remove();
                
                canvas.style.display = 'none';
                
                // Check if empty message already exists
                let emptyMsg = canvas.parentNode.querySelector('.chart-empty');
                if (!emptyMsg) {
                    emptyMsg = document.createElement('div');
                    emptyMsg.className = 'chart-empty text-muted';
                    emptyMsg.style.textAlign = 'center';
                    emptyMsg.style.padding = '3rem';
                    emptyMsg.style.background = '#f8fafc';
                    emptyMsg.style.borderRadius = '0.5rem';
                    emptyMsg.innerHTML = `
                        <i class="fas fa-chart-line" style="font-size: 3rem; opacity: 0.3; margin-bottom: 1rem;"></i>
                        <br>
                        <span style="font-weight: 500;">${message || 'No data available'}</span>
                        <br>
                        <small style="display: block; margin-top: 0.5rem;">Add student records to see analytics</small>
                    `;
                    canvas.parentNode.appendChild(emptyMsg);
                }
            }
        });
    }

    // ========== RENDER CHARTS ==========
    window.renderCharts = function(data) {
        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('❌ Chart.js not loaded');
            return;
        }

        // Remove loading states
        document.querySelectorAll('.chart-loading, .chart-empty').forEach(el => el.remove());
        
        const chartDefaults = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        font: { 
                            family: "'Inter', sans-serif", 
                            size: 12,
                            weight: '500' 
                        },
                        color: '#475569'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleFont: { family: "'Inter', sans-serif", weight: '600' },
                    bodyFont: { family: "'Inter', sans-serif" },
                    padding: 12,
                    cornerRadius: 8
                }
            }
        };

        // 1. Subject-wise Performance Chart
        const subjectCanvas = document.getElementById('subjectChart');
        if (subjectCanvas) {
            // Destroy existing chart
            if (subjectCanvas.chart instanceof Chart) {
                subjectCanvas.chart.destroy();
            }
            
            subjectCanvas.style.display = 'block';
            const ctxSubject = subjectCanvas.getContext('2d');
            
            subjectCanvas.chart = new Chart(ctxSubject, {
                type: 'bar',
                data: {
                    labels: data.subjects || [],
                    datasets: [{
                        label: 'Average Marks',
                        data: data.subject_averages || [],
                        backgroundColor: 'rgba(30, 58, 138, 0.8)',
                        borderColor: '#1e3a8a',
                        borderWidth: 2,
                        borderRadius: 6,
                        hoverBackgroundColor: 'rgba(30, 58, 138, 1)',
                        barPercentage: 0.7,
                        categoryPercentage: 0.8
                    }]
                },
                options: {
                    ...chartDefaults,
                    plugins: {
                        ...chartDefaults.plugins,
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: { 
                                color: '#f1f5f9',
                                drawBorder: false
                            },
                            ticks: { 
                                callback: value => value + '%',
                                stepSize: 20
                            },
                            title: {
                                display: true,
                                text: 'Marks (%)',
                                font: { weight: '600', size: 12 },
                                color: '#64748b'
                            }
                        },
                        x: { 
                            grid: { display: false },
                            ticks: { font: { weight: '500' } }
                        }
                    },
                    animation: {
                        duration: 1000,
                        easing: 'easeInOutQuart'
                    }
                }
            });
        }

        // 2. Marks Distribution Chart
        const distCanvas = document.getElementById('distributionChart');
        if (distCanvas) {
            if (distCanvas.chart instanceof Chart) {
                distCanvas.chart.destroy();
            }
            
            distCanvas.style.display = 'block';
            const ctxDist = distCanvas.getContext('2d');
            
            distCanvas.chart = new Chart(ctxDist, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(data.distribution || {}),
                    datasets: [{
                        data: Object.values(data.distribution || {}),
                        backgroundColor: [
                            '#ef4444', // Fail
                            '#f59e0b', // Average
                            '#3b82f6', // Good
                            '#10b981'  // Excellent
                        ],
                        hoverBackgroundColor: [
                            '#dc2626',
                            '#d97706',
                            '#2563eb',
                            '#059669'
                        ],
                        hoverOffset: 15,
                        borderWidth: 0
                    }]
                },
                options: {
                    ...chartDefaults,
                    cutout: '70%',
                    plugins: {
                        ...chartDefaults.plugins,
                        legend: { 
                            position: 'bottom', 
                            labels: { 
                                padding: 20,
                                usePointStyle: true,
                                pointStyle: 'circle'
                            } 
                        }
                    },
                    animation: {
                        animateRotate: true,
                        animateScale: true,
                        duration: 1200
                    }
                }
            });
        }

        // 3. Attendance vs Marks Scatter Chart
        const scatterCanvas = document.getElementById('scatterChart');
        if (scatterCanvas) {
            if (scatterCanvas.chart instanceof Chart) {
                scatterCanvas.chart.destroy();
            }
            
            scatterCanvas.style.display = 'block';
            const ctxScatter = scatterCanvas.getContext('2d');
            
            scatterCanvas.chart = new Chart(ctxScatter, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'Students',
                        data: (data.attendance_marks || []).map(item => ({ 
                            x: parseFloat(item.attendance) || 0, 
                            y: parseFloat(item.marks) || 0 
                        })),
                        backgroundColor: 'rgba(220, 38, 38, 0.7)',
                        borderColor: 'rgba(220, 38, 38, 0.9)',
                        borderWidth: 1,
                        pointRadius: 6,
                        pointHoverRadius: 10,
                        pointBorderColor: 'white',
                        pointBorderWidth: 2
                    }]
                },
                options: {
                    ...chartDefaults,
                    scales: {
                        x: {
                            title: { 
                                display: true, 
                                text: 'Attendance (%)', 
                                font: { weight: '600', size: 12 },
                                color: '#64748b'
                            },
                            min: 0,
                            max: 100,
                            grid: { 
                                color: '#f1f5f9',
                                drawBorder: false
                            },
                            ticks: { stepSize: 20 }
                        },
                        y: {
                            title: { 
                                display: true, 
                                text: 'Marks', 
                                font: { weight: '600', size: 12 },
                                color: '#64748b'
                            },
                            min: 0,
                            max: 100,
                            grid: { 
                                color: '#f1f5f9',
                                drawBorder: false
                            },
                            ticks: { stepSize: 20 }
                        }
                    },
                    animation: {
                        duration: 1000,
                        easing: 'easeInOutQuart'
                    }
                }
            });
        }

        // Hide loading messages
        document.querySelectorAll('.chart-loading').forEach(el => el.remove());
    };

    // ========== INITIALIZE ==========
    // Initialize dashboard charts if on dashboard page
    if (document.getElementById('subjectChart')) {
        // Small delay to ensure DOM is fully ready
        setTimeout(initDashboardCharts, 100);
    }

    // ========== FORM VALIDATION ==========
    const markInputs = document.querySelectorAll('input[name^="marks_"], input[name="marks"]');
    markInputs.forEach(input => {
        input.addEventListener('input', function() {
            let value = parseInt(this.value);
            if (this.value === '') return;
            if (isNaN(value)) {
                this.value = '';
            } else if (value < 0) {
                this.value = 0;
            } else if (value > 100) {
                this.value = 100;
            }
        });
    });

    const attendanceInputs = document.querySelectorAll('input[name="attendance"]');
    attendanceInputs.forEach(input => {
        input.addEventListener('input', function() {
            let value = parseInt(this.value);
            if (this.value === '') return;
            if (isNaN(value)) {
                this.value = '';
            } else if (value < 0) {
                this.value = 0;
            } else if (value > 100) {
                this.value = 100;
            }
        });
    });

    // ========== CONFIRM DELETE ==========
    const deleteLinks = document.querySelectorAll('a[href^="/delete/"]');
    deleteLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (!confirm('⚠️ Are you sure you want to delete this record? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    console.log('✅ Student Portal JS initialized');
});