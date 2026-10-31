(() => {
    "use strict";

    const routes = new Set([
        "/", "/reels", "/profile", "/analytics", "/history"
    ]);

    if (typeof I18N !== "undefined") {
        Object.assign(I18N.uz, {
            home_heading: "Bugun nimani boshqaramiz?",
            home_sub: "Kontent yaratish uchun shaxsiy boshqaruv markazing.",
            module_video: "Reels joylash",
            module_profile: "Instagram profil",
            module_stats: "Statistika",
            module_history: "Kontent tarixi",
            launch_action: "Bo‘limni ochish",
            home_back: "Bosh sahifa"
        });

        Object.assign(I18N.ru, {
            home_heading: "Что будем делать сегодня?",
            home_sub: "Твоё личное пространство для управления контентом.",
            module_video: "Публикация Reels",
            module_profile: "Профиль Instagram",
            module_stats: "Статистика",
            module_history: "История контента",
            launch_action: "Открыть раздел",
            home_back: "Главная"
        });

        Object.assign(I18N.en, {
            home_heading: "What would you like to manage today?",
            home_sub: "Your personal command center for content creation.",
            module_video: "Publish a Reel",
            module_profile: "Instagram profile",
            module_stats: "Analytics",
            module_history: "Content library",
            launch_action: "Open workspace",
            home_back: "Home"
        });
    }

    // Markaziy loading oynasi
    const loader = document.createElement("div");
    loader.className = "studio-loader is-visible";
    loader.setAttribute("aria-live", "polite");
    loader.innerHTML = `
        <div class="studio-loader-content">
            <div class="studio-diamond-loader" aria-hidden="true">
                <span></span><span></span><span></span><span></span>
            </div>
            <div class="studio-loader-title">Insta AI Studio</div>
            <div class="studio-loader-message">Ish maydoni tayyorlanmoqda...</div>
        </div>
    `;

    document.body.appendChild(loader);

    let startupActive = true;
    let pendingRequests = 0;
    let pageLoaded = document.readyState === "complete";
    let hideTimer = null;
    const startTime = performance.now();

    function showLoader(message) {
        if (message) {
            const label = loader.querySelector(".studio-loader-message");
            if (label) label.textContent = message;
        }

        clearTimeout(hideTimer);
        loader.classList.remove("is-hidden");
        loader.classList.add("is-visible");
    }

    function hideLoader() {
        loader.classList.remove("is-visible");
        loader.classList.add("is-hidden");
    }

    function scheduleHide() {
        if (!pageLoaded || pendingRequests > 0 || !startupActive) return;

        clearTimeout(hideTimer);

        const minimumTime = 650;
        const elapsed = performance.now() - startTime;
        const remaining = Math.max(0, minimumTime - elapsed);

        hideTimer = setTimeout(() => {
            if (pendingRequests === 0) {
                startupActive = false;
                hideLoader();
            }
        }, remaining);
    }

    // Dastlabki API so'rovlari davomida loader ko'rinadi.
    const originalFetch = window.fetch.bind(window);

    window.fetch = function(input, init) {
        const url = typeof input === "string"
            ? input
            : (input && input.url) || "";

        const tracked = startupActive && url.includes("/api/");

        if (tracked) {
            pendingRequests++;
            showLoader("Ma'lumotlar yuklanmoqda...");
        }

        return originalFetch(input, init).finally(() => {
            if (tracked) {
                pendingRequests = Math.max(0, pendingRequests - 1);
                scheduleHide();
            }
        });
    };

    window.addEventListener("load", () => {
        pageLoaded = true;
        scheduleHide();
    }, { once: true });

    // Kutilmagan juda uzoq kutishni cheklash.
    setTimeout(() => {
        if (startupActive) {
            startupActive = false;
            hideLoader();
        }
    }, 20000);

    // Ichki sahifalarda bosh sahifaga qaytish.
    const page = document.body.dataset.page;
    const topbarLeft = document.querySelector(".topbar-left");

    if (page !== "dashboard" && topbarLeft &&
        !document.querySelector(".workspace-back")) {
        const back = document.createElement("a");
        back.href = "/";
        back.className = "workspace-back";
        back.innerHTML = '<span class="workspace-back-icon">←</span><span data-i18n="home_back">Bosh sahifa</span>';
        topbarLeft.prepend(back);
    }

    // Chiqish tugmasi.
    const topActions = document.querySelector(".top-actions");

    if (topActions && !document.querySelector(".workspace-logout")) {
        const logout = document.createElement("a");
        logout.href = "/logout";
        logout.className = "workspace-logout";
        logout.innerHTML = '<span>↗</span><span data-i18n="logout">Chiqish</span>';
        topActions.appendChild(logout);
    }

    document.documentElement.classList.add("workspace-enter");

    // Bo'limni ochishda tanlangan romb tugma ekran chetiga siljiydi.
    document.addEventListener("click", (event) => {
        const link = event.target.closest("a[href]");

        if (
            !link ||
            event.defaultPrevented ||
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey ||
            link.target ||
            link.hasAttribute("download")
        ) return;

        const target = new URL(link.href, window.location.href);
        const path = target.pathname.replace(/\/+$/, "") || "/";

        if (target.origin !== window.location.origin) return;
        if (!routes.has(path)) return;

        const current = location.pathname.replace(/\/+$/, "") || "/";
        if (path === current) return;

        event.preventDefault();

        const card = link.closest(".launcher-card");

        if (card) {
            const rect = card.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;

            const edges = [
                { name: "top", distance: cy },
                { name: "right", distance: innerWidth - cx },
                { name: "bottom", distance: innerHeight - cy },
                { name: "left", distance: cx }
            ];

            edges.sort((a, b) => a.distance - b.distance);

            let dx = 0;
            let dy = 0;

            switch (edges[0].name) {
                case "top":
                    dy = -cy - rect.height / 2 - 30;
                    break;
                case "right":
                    dx = innerWidth - cx + rect.width / 2 + 30;
                    break;
                case "bottom":
                    dy = innerHeight - cy + rect.height / 2 + 30;
                    break;
                case "left":
                    dx = -cx - rect.width / 2 - 30;
                    break;
            }

            card.style.setProperty("--fly-x", `${Math.round(dx)}px`);
            card.style.setProperty("--fly-y", `${Math.round(dy)}px`);
            card.classList.add("is-opening");

            document.querySelectorAll(".launcher-card:not(.is-opening)")
                .forEach(item => item.classList.add("is-dimmed"));
        } else {
            document.documentElement.classList.add("page-is-leaving");
        }

        window.setTimeout(() => {
            startupActive = false;
            showLoader("Bo‘lim ochilmoqda...");
        }, 140);

        window.setTimeout(() => {
            window.location.assign(path);
        }, 450);

    }, true);
})();
