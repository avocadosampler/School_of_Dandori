let courses = [];
let filters = { types: [], locations: [] };
let currentFilters = { type: 'All', location: 'All' };

// Initialize app
async function init() {
    await loadFilters();
    await loadCourses();
    renderFilters();
    renderCourses();
}

// Load filter options
async function loadFilters() {
    const response = await fetch('/api/filters');
    filters = await response.json();
}

// Load courses
async function loadCourses() {
    const params = new URLSearchParams(currentFilters);
    const response = await fetch(`/api/courses?${params}`);
    courses = await response.json();
}


// Render filter buttons
function renderFilters() {
    const typeFilters = document.getElementById('typeFilters');
    const locationFilters = document.getElementById('locationFilters');
    
    typeFilters.innerHTML = filters.types.map(type => `
        <button class="filter-btn ${currentFilters.type === type ? 'active' : ''}" 
                onclick="setTypeFilter('${type}')">
            ${type}
        </button>
    `).join('');
    
    locationFilters.innerHTML = filters.locations.map(loc => `
        <button class="location-btn ${currentFilters.location === loc ? 'active' : ''}" 
                onclick="setLocationFilter('${loc}')">
            ${loc}
        </button>
    `).join('');
}

// Set type filter
async function setTypeFilter(type) {
    currentFilters.type = type;
    await loadCourses();
    renderFilters();
    renderCourses();
}

// Set location filter
async function setLocationFilter(location) {
    currentFilters.location = location;
    await loadCourses();
    renderFilters();
    renderCourses();
}

// Render courses grid
function renderCourses() {
    const grid = document.getElementById('coursesGrid');
    grid.innerHTML = courses.map(course => {
        const summary = course.course_description.length > 140
            ? course.course_description.substring(0, 140) + '...'
            : course.course_description;
        
        return `
            <div class="course-card" onclick='showCourseDetails(${JSON.stringify(course).replace(/'/g, "&apos;")})'>
                <div>
                    <div class="card-header">
                        <span class="course-type">${course.course_type}</span>
                        <span class="course-location">${course.course_location.toUpperCase()}</span>
                    </div>
                    <h3 class="course-title">${course.course_name}</h3>
                    <p class="course-description">${summary}</p>
                </div>
                
                <div class="card-footer">
                    <div class="instructor-info">
                        <span class="instructor-label">Mentor</span>
                        <span class="instructor-name">${course.course_instructor}</span>
                    </div>
                    <button class="arrow-btn">→</button>
                </div>
            </div>
        `;
    }).join('');
}

// Show course details modal
function showCourseDetails(course) {
    const modal = document.getElementById('courseModal');
    const modalContent = document.getElementById('modalContent');
    
    const objectives = course.course_objectives.split('. ').filter(o => o.trim());
    const materials = course.course_materials.split('\n');
    const skills = course.course_skills.split(',');
    
    modalContent.innerHTML = `
        <button class="close-btn" onclick="closeModal()">×</button>
        
        <div class="modal-header">
            <div class="modal-logo">🎓</div>
            <h1 class="modal-title">${course.course_name}</h1>
            <div class="title-divider"></div>
            
            <div class="info-grid">
                <div class="info-card">
                    <span class="info-label">Instructor</span>
                    <span class="info-value">${course.course_instructor}</span>
                </div>
                <div class="info-card">
                    <span class="info-label">Location</span>
                    <span class="info-value">${course.course_location}</span>
                </div>
                <div class="info-card">
                    <span class="info-label">Category</span>
                    <span class="info-value">${course.course_type}</span>
                </div>
                <div class="info-card cost">
                    <span class="info-label">Fee</span>
                    <span class="info-value">${course.course_cost}</span>
                </div>
            </div>
        </div>

        <div class="modal-body">
            <div>
                <section class="section">
                    <h2 class="section-title">
                        <span class="title-bar"></span>
                        The Journey
                    </h2>
                    <p class="section-text">${course.course_description}</p>
                </section>

                <section class="section">
                    <h2 class="section-title">
                        <span class="title-bar"></span>
                        Learning Objectives
                    </h2>
                    <ul class="objectives-list">
                        ${objectives.map(obj => `
                            <li class="objective-item">
                                <div class="objective-dot">
                                    <div class="objective-dot-inner"></div>
                                </div>
                                <span class="objective-text">${obj.trim()}${obj.endsWith('.') ? '' : '.'}</span>
                            </li>
                        `).join('')}
                    </ul>
                </section>
            </div>

            <div class="sidebar">
                <section class="materials-section">
                    <h2 class="sidebar-title">Included Materials</h2>
                    <div class="materials-list">
                        ${materials.map(mat => `
                            <div class="material-item">
                                <span class="checkmark">✓</span>
                                ${mat.trim()}
                            </div>
                        `).join('')}
                    </div>
                </section>

                <section class="skills-section">
                    <div class="skills-bg">🎓</div>
                    <h2 class="sidebar-title">Skills Gained</h2>
                    <div class="skills-list">
                        ${skills.map(skill => `
                            <span class="skill-tag">${skill.trim()}</span>
                        `).join('')}
                    </div>
                    <button class="enrol-modal-btn">Enrol Now</button>
                </section>
                
                <div class="course-id">
                    <p class="course-id-text">Class Reference: ${course.course_id}</p>
                </div>
            </div>
        </div>
    `;
    
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Close modal
function closeModal() {
    const modal = document.getElementById('courseModal');
    modal.classList.remove('active');
    document.body.style.overflow = 'auto';
}

// Close modal on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop')) {
        closeModal();
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);
