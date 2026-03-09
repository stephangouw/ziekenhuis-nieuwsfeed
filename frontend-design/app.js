/**
 * ZorgNieuws Frontend Logic
 * Refined Editorial / Medical Elegance Aesthetic
 */

document.addEventListener('DOMContentLoaded', () => {
    const newsContainer = document.getElementById('news-container');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const template = document.getElementById('article-template');

    let articlesData = [];

    // Initialize application
    init();

    async function init() {
        try {
            // In a real staging/prod setup, this would hit an API endpoint.
            // For now, we fetch the generated static JSON relative to this file.
            const response = await fetch('data.json');
            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();
            articlesData = data.articles || [];

            // Render initial view
            renderArticles('all');

            // Setup listeners
            setupFilters();

        } catch (error) {
            console.error('Failed to fetch news data:', error);
            renderErrorState();
        }
    }

    function setupFilters() {
        filterButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Update active state
                filterButtons.forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');

                // Filter and render
                const filterValue = e.target.getAttribute('data-filter');
                renderArticles(filterValue);
            });
        });
    }

    function renderArticles(filter) {
        // Clear container
        newsContainer.innerHTML = '';

        // Filter data
        let filteredData = articlesData;
        if (filter !== 'all') {
            filteredData = articlesData.filter(article => article.network === filter);
        }

        // Empty state check
        if (filteredData.length === 0) {
            renderEmptyState(filter);
            return;
        }

        // Render cards with staggered animation
        filteredData.forEach((article, index) => {
            const clone = template.content.cloneNode(true);
            const card = clone.querySelector('.news-card');

            // Stagger animation delay
            card.style.animationDelay = `${index * 0.05}s`;

            // Populate data
            clone.querySelector('.hospital-name').textContent = article.hospital_name;

            // Format date
            const dateObj = new Date(article.date_published);
            const dateStr = isNaN(dateObj)
                ? article.date_published
                : dateObj.toLocaleDateString('nl-NL', { day: 'numeric', month: 'long', year: 'numeric' });
            clone.querySelector('.publish-date').textContent = dateStr;

            // Title & Link
            const link = clone.querySelector('.title-link');
            link.textContent = article.title;
            link.href = article.url;

            // Summary
            clone.querySelector('.card-summary').textContent = article.ai_summary || "Geen samenvatting beschikbaar.";

            // Tags
            const tagGroup = clone.querySelector('.tag-group');
            if (article.tags && Array.isArray(article.tags)) {
                article.tags.forEach(tagText => {
                    const tagEl = document.createElement('span');
                    tagEl.className = 'tag';
                    tagEl.textContent = tagText;
                    tagGroup.appendChild(tagEl);
                });
            }

            // Network Badge for editorial layout aesthetic
            clone.querySelector('.network-badge').textContent = article.network;

            newsContainer.appendChild(clone);
        });
    }

    function renderEmptyState(filter) {
        const div = document.createElement('div');
        div.className = 'empty-state fade-in';

        if (filter === 'all') {
            div.innerHTML = `
                <p>Nog geen nieuwsberichten beschikbaar.</p>
                <p style="font-size: 0.8rem; margin-top: 1rem; font-family: var(--font-body); color: var(--text-meta);">
                De backend ophaal-cyclus heeft nog geen gegevens verzameld of verwerkt.
                </p>
            `;
        } else {
            div.innerHTML = `<p>Geen nieuws gevonden voor netwerk: <strong>${filter}</strong>.</p>`;
        }

        newsContainer.appendChild(div);
    }

    function renderErrorState() {
        newsContainer.innerHTML = `
            <div class="empty-state fade-in" style="color: #ef4444;">
                <p>Er is een probleem opgetreden bij het laden van het nieuws.</p>
                <p style="font-size: 0.8rem; margin-top: 1rem; font-family: var(--font-body);">Zorg dat data.json beschikbaar is.</p>
            </div>
        `;
    }
});
