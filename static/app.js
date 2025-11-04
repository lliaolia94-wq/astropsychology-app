// API Base URL
const API_BASE = '';

// State
let currentChartData = null;

// PWA: Регистрация Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        console.log('SW registered: ', registration);
      })
      .catch((registrationError) => {
        console.log('SW registration failed: ', registrationError);
      });
  });
}

// PWA: Обработка установки
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  // Предотвращаем автоматическое появление баннера
  e.preventDefault();
  deferredPrompt = e;
  
  // Показываем кнопку установки (можно добавить UI)
  showInstallButton();
});

function showInstallButton() {
  // Можно добавить кнопку установки в интерфейс
  console.log('PWA можно установить');
}

// PWA: Установка приложения
window.installPWA = async () => {
  if (!deferredPrompt) return;
  
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  console.log(`User response to the install prompt: ${outcome}`);
  deferredPrompt = null;
};

// DOM Elements
const chartForm = document.getElementById('chart-form');
const calculateBtn = document.getElementById('calculate-btn');
const newChartBtn = document.getElementById('new-chart-btn');
const getInterpretationBtn = document.getElementById('get-interpretation-btn');

// Step management
function showStep(stepId) {
    document.querySelectorAll('.step').forEach(step => {
        step.classList.remove('active');
    });
    document.getElementById(stepId).classList.add('active');
    document.getElementById('error-message').style.display = 'none';
}

function showError(message) {
    document.getElementById('error-text').textContent = message;
    document.getElementById('error-message').style.display = 'block';
    showStep('step-input');
}

// Form submission
chartForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('name').value || 'Гость',
        birth_date: document.getElementById('birth-date').value,
        birth_time: document.getElementById('birth-time').value || '12:00',
        birth_place: document.getElementById('birth-place').value,
        birth_country: document.getElementById('birth-country').value || null,
        houses_system: 'placidus'
    };

    // Validate
    if (!formData.birth_date || !formData.birth_time || !formData.birth_place) {
        showError('Пожалуйста, заполните все обязательные поля');
        return;
    }

    // Show loading
    showStep('step-loading');
    calculateBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/guest/calculate-chart`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || data.detail || 'Ошибка расчета карты');
        }

        currentChartData = data.chart_data;
        displayChartResults(data);

    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Произошла ошибка при расчете карты. Попробуйте еще раз.');
    } finally {
        calculateBtn.disabled = false;
    }
});

// Display chart results
function displayChartResults(data) {
    const mainSigns = data.main_signs;
    
    // Display main signs
    document.getElementById('sun-sign').textContent = formatSign(mainSigns.sun);
    document.getElementById('moon-sign').textContent = formatSign(mainSigns.moon);
    document.getElementById('asc-sign').textContent = formatSign(mainSigns.ascendant);

    // Display planets
    const planetsGrid = document.getElementById('planets-grid');
    planetsGrid.innerHTML = '';
    
    const planets = data.chart_data.planets || {};
    const planetNames = {
        'sun': 'Солнце',
        'moon': 'Луна',
        'mercury': 'Меркурий',
        'venus': 'Венера',
        'mars': 'Марс',
        'jupiter': 'Юпитер',
        'saturn': 'Сатурн',
        'uranus': 'Уран',
        'neptune': 'Нептун',
        'pluto': 'Плутон',
        'true_node': 'Лунный Узел'
    };

    Object.entries(planets).forEach(([planetKey, planetData]) => {
        const planetItem = document.createElement('div');
        planetItem.className = 'planet-item';
        
        const planetName = planetNames[planetKey] || planetKey;
        const zodiacSign = formatSign(planetData.zodiac_sign);
        const house = planetData.house || '-';
        const retrograde = planetData.is_retrograde ? ' (R)' : '';
        
        planetItem.innerHTML = `
            <div class="planet-name">${planetName}${retrograde}</div>
            <div class="planet-sign">${zodiacSign}</div>
            <div class="planet-house">Дом ${house}</div>
        `;
        
        planetsGrid.appendChild(planetItem);
    });

    // Show interpretation button
    getInterpretationBtn.style.display = 'block';
    document.getElementById('interpretation-content').innerHTML = '';

    showStep('step-results');
}

// Format zodiac sign
function formatSign(sign) {
    if (!sign) return '-';
    
    const signMap = {
        'aries': 'Овен',
        'taurus': 'Телец',
        'gemini': 'Близнецы',
        'cancer': 'Рак',
        'leo': 'Лев',
        'virgo': 'Дева',
        'libra': 'Весы',
        'scorpio': 'Скорпион',
        'sagittarius': 'Стрелец',
        'capricorn': 'Козерог',
        'aquarius': 'Водолей',
        'pisces': 'Рыбы'
    };
    
    return signMap[sign.toLowerCase()] || sign;
}

// Get AI interpretation
getInterpretationBtn.addEventListener('click', async () => {
    if (!currentChartData) return;

    const interpretationLoading = document.getElementById('interpretation-loading');
    const interpretationContent = document.getElementById('interpretation-content');
    
    interpretationLoading.style.display = 'flex';
    getInterpretationBtn.style.display = 'none';
    interpretationContent.innerHTML = '';

    try {
        const response = await fetch(`${API_BASE}/api/guest/ai-interpretation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chart_data: currentChartData,
                template_type: 'natal_analysis'
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.detail || 'Ошибка генерации интерпретации');
        }

        interpretationContent.innerHTML = formatInterpretation(data.interpretation);

    } catch (error) {
        console.error('Error:', error);
        interpretationContent.innerHTML = `<p style="color: var(--error-color);">Ошибка: ${error.message}</p>`;
        getInterpretationBtn.style.display = 'block';
    } finally {
        interpretationLoading.style.display = 'none';
    }
});

// Format interpretation text
function formatInterpretation(text) {
    // Split by emoji markers and format
    const sections = text.split(/(?=💫|🔍|🏛️|🛠️|📈|🌟)/);
    
    return sections.map(section => {
        if (!section.trim()) return '';
        
        const lines = section.split('\n').filter(line => line.trim());
        if (lines.length === 0) return '';
        
        const firstLine = lines[0];
        const rest = lines.slice(1).join('\n');
        
        return `<p><strong>${firstLine}</strong></p><p>${rest}</p>`;
    }).join('');
}

// New chart button
newChartBtn.addEventListener('click', () => {
    currentChartData = null;
    chartForm.reset();
    document.getElementById('name').value = 'Гость';
    showStep('step-input');
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

// City autocomplete (optional enhancement)
const birthPlaceInput = document.getElementById('birth-place');
let autocompleteTimeout = null;

birthPlaceInput.addEventListener('input', async (e) => {
    const query = e.target.value;
    
    if (query.length < 2) return;
    
    clearTimeout(autocompleteTimeout);
    autocompleteTimeout = setTimeout(async () => {
        try {
            const response = await fetch(`${API_BASE}/api/geocoding/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    limit: 5
                })
            });

            if (response.ok) {
                const data = await response.json();
                // You can implement autocomplete dropdown here
                console.log('Suggestions:', data.cities);
            }
        } catch (error) {
            console.error('Autocomplete error:', error);
        }
    }, 300);
});

