<script id="GV_SHARED_RESERVATION_CALENDAR_V1">
(function () {
    "use strict";

function getQueryDate() {
        const params = new URLSearchParams(window.location.search);
        const value = params.get("date");

        if (!value || !/^\\d{4}-\\d{2}-\\d{2}$/.test(value)) {
            return null;
        }

        return value;
    }

    function getBookingId() {
        const params = new URLSearchParams(window.location.search);
        const value = params.get("booking_id");

        if (!value || !/^\\d+$/.test(value)) {
            return null;
        }

        return value;
    }

    const queryDate = getQueryDate();
    const queryBookingId = getBookingId();



    const state = {
        startDate: queryDate
            ? parseDate(queryDate)
            : startOfDay(new Date()),
        selectedDate: queryDate,
        days: [],
        monthCursor: queryDate
            ? parseDate(queryDate)
            : startOfDay(new Date()),
    };


    const faWeekdays = [
        "دوشنبه",
        "سه‌شنبه",
        "چهارشنبه",
        "پنجشنبه",
        "جمعه",
        "شنبه",
        "یکشنبه"
    ];

    function startOfDay(date) {
        return new Date(
            date.getFullYear(),
            date.getMonth(),
            date.getDate()
        );
    }

    function pad(value) {
        return String(value).padStart(2, "0");
    }

    function isoDate(date) {
        return (
            date.getFullYear() +
            "-" +
            pad(date.getMonth() + 1) +
            "-" +
            pad(date.getDate())
        );
    }

    function parseDate(value) {
        const [year, month, day] = value.split("-").map(Number);
        return new Date(year, month - 1, day);
    }

    function formatDate(value) {
        return new Intl.DateTimeFormat("fa-IR", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
        }).format(parseDate(value));
    }

    function formatShortDate(value) {
        return new Intl.DateTimeFormat("fa-IR", {
            month: "long",
            day: "numeric",
        }).format(parseDate(value));
    }

    function formatTime(value) {
        const date = new Date(value);
        return pad(date.getHours()) + ":" + pad(date.getMinutes());
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    async function loadOverview() {
        const response = await fetch(
            "/dashboard/api/reservations/overview?start_date=" +
            encodeURIComponent(isoDate(state.startDate)) +
            (queryBookingId
                ? "&booking_id=" + encodeURIComponent(queryBookingId)
                : "") +
            "&days=7",
            {
                credentials: "same-origin",
                cache: "no-store",
            }
        );

        if (!response.ok) {
            throw new Error("overview_request_failed");
        }

        const data = await response.json();

        state.days = data.days || [];

        if (
            queryBookingId ||
            !state.selectedDate ||
            !state.days.some(day => day.date === state.selectedDate)
        ) {
            state.selectedDate = data.start_date;
            state.monthCursor = parseDate(data.start_date);
        }

        const pendingBox = document.getElementById("pendingBox");

        pendingBox.innerHTML =
            data.pending_requests > 0
                ? `<div class="rv-pending">
                    🔔 ${Number(data.pending_requests).toLocaleString("fa-IR")}
                    درخواست ویزیت هنوز زمان‌بندی نشده است.
                  </div>`
                : "";

        renderDays();
        renderSelectedDay();
    }

    function renderDays() {
        const root = document.getElementById("daysGrid");

        root.innerHTML = state.days.map(day => {
            const events = day.events || [];

            return `
                <article
                    class="rv-card rv-day
                    ${day.is_today ? "today" : ""}
                    ${day.date === state.selectedDate ? "selected" : ""}"
                    data-date="${day.date}"
                >
                    <div class="rv-day-head">
                        <div>
                            <div class="rv-day-name">
                                ${escapeHtml(day.weekday)}
                            </div>
                            <div class="rv-day-date">
                                ${escapeHtml(formatShortDate(day.date))}
                            </div>
                        </div>

                        <div class="rv-count">
                            ${Number(day.count || 0).toLocaleString("fa-IR")}
                        </div>
                    </div>

                    ${
                        events.length
                            ? events.slice(0, 5).map(event => `
                                <div class="rv-event">
                                    <div class="rv-time">
                                        ${formatTime(event.start_at)}
                                    </div>

                                    <div class="rv-event-main">
                                        <div class="rv-event-name">
                                            ${escapeHtml(event.name)}
                                        </div>

                                        <div class="rv-source">
                                            ${escapeHtml(event.source_label)}
                                        </div>
                                    </div>
                                </div>
                            `).join("")
                            : `
                                <div class="rv-empty">
                                    رزروی برای این روز ثبت نشده.
                                </div>
                            `
                    }

                    ${
                        events.length > 5
                            ? `
                                <div class="rv-empty">
                                    + ${events.length - 5} مورد دیگر
                                </div>
                              `
                            : ""
                    }
                </article>
            `;
        }).join("");

        root.querySelectorAll("[data-date]").forEach(node => {
            node.addEventListener("click", () => {
                state.selectedDate = node.dataset.date;
                renderDays();
                renderSelectedDay();
            });
        });
    }

    function renderSelectedDay() {
        const day = state.days.find(
            item => item.date === state.selectedDate
        );

        if (!day) {
            return;
        }

        document.getElementById("selectedDateTitle").textContent =
            formatDate(day.date);

        const details = document.getElementById("detailsList");
        const slotGrid = document.getElementById("slotGrid");

        const events = day.events || [];
        const slots = day.slots || [];

        details.innerHTML = events.length
            ? events.map(event => `
                <div class="rv-item">
                    <div class="rv-item-head">
                        <div class="rv-item-name">
                            ${escapeHtml(event.name)}
                        </div>
                        <strong>
                            ${formatTime(event.start_at)}
                        </strong>
                    </div>

                    <div class="rv-item-meta">
                        ${escapeHtml(event.source_label)}
                        ${
                            event.phone
                                ? " · " + escapeHtml(event.phone)
                                : ""
                        }
                    </div>
                </div>
            `).join("")
            : `
                <div class="rv-empty">
                    برای این روز رزروی ثبت نشده است.
                </div>
            `;

        slotGrid.innerHTML = slots.length
            ? slots.map(slot => `
                <div class="rv-slot ${slot.enabled ? "" : "off"}">
                    <span class="rv-slot-time">
                        ${formatTime(slot.start_at)}
                    </span>

                    <button
                        type="button"
                        class="rv-switch ${slot.enabled ? "on" : "off"}"
                        onclick="toggleSlot(${slot.id}, ${!slot.enabled})"
                    >
                        ${slot.enabled ? "فعال" : "غیرفعال"}
                    </button>
                </div>
            `).join("")
            : `
                <div class="rv-empty">
                    برای این روز Slot ثبت نشده است.
                </div>
            `;
    }

    window.toggleSlot = async function (slotId, enabled) {
        try {
            const response = await fetch(
                "/booking/api/slots/" +
                encodeURIComponent(slotId) +
                "/toggle-enabled?enabled=" +
                encodeURIComponent(enabled ? "true" : "false"),
                {
                    method: "POST",
                    credentials: "same-origin",
                }
            );

            if (!response.ok) {
                throw new Error("toggle_failed");
            }

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || "toggle_failed");
            }

            await loadOverview();

        } catch (error) {
            console.error(error);
            alert("تغییر وضعیت Slot انجام نشد.");
        }
    };

    window.shiftDays = function (amount) {
        state.startDate = startOfDay(state.startDate);
        state.startDate.setDate(
            state.startDate.getDate() + amount
        );
        state.selectedDate = null;
        loadOverview().catch(console.error);
        window.scrollTo({ top: 0, behavior: "smooth" });
    };

    window.goToday = function () {
        state.startDate = startOfDay(new Date());
        state.selectedDate = null;
        loadOverview().catch(console.error);
        window.scrollTo({ top: 0, behavior: "smooth" });
    };

    window.toggleMonth = function () {
        const card = document.getElementById("monthCard");

        card.classList.toggle("open");

        if (card.classList.contains("open")) {
            renderMonth();
        }
    };

    window.changeMonth = function (amount) {
        state.monthCursor.setMonth(
            state.monthCursor.getMonth() + amount
        );
        renderMonth();
    };

    function renderMonth() {
        const root = document.getElementById("monthGrid");

        document.getElementById("monthTitle").textContent =
            new Intl.DateTimeFormat("fa-IR", {
                month: "long",
                year: "numeric",
            }).format(state.monthCursor);

        const year = state.monthCursor.getFullYear();
        const month = state.monthCursor.getMonth();

        const first = new Date(year, month, 1);
        const last = new Date(year, month + 1, 0);

        let html = faWeekdays.map(day =>
            `<div class="rv-month-weekday">${day.slice(0,1)}</div>`
        ).join("");

        // JS Sunday = 0. Persian/Jalali UI is Saturday-first, but
        // the Gregorian monthly visual is kept stable here.
        const offset = first.getDay();

        for (let i = 0; i < offset; i++) {
            html += `<div class="rv-month-day empty"></div>`;
        }

        for (let dayNumber = 1; dayNumber <= last.getDate(); dayNumber++) {
            const date = new Date(year, month, dayNumber);
            const key = isoDate(date);

            const sourceDay = state.days.find(
                item => item.date === key
            );

            const count = sourceDay ? sourceDay.count : 0;

            html += `
                <div
                    class="rv-month-day
                    ${key === state.selectedDate ? "selected" : ""}"
                    onclick="jumpToDate('${key}')"
                >
                    <div class="rv-month-number">
                        ${dayNumber.toLocaleString("fa-IR")}
                    </div>

                    <div class="rv-month-count">
                        ${
                            count
                                ? Number(count).toLocaleString("fa-IR") + " رزرو"
                                : "—"
                        }
                    </div>
                </div>
            `;
        }

        root.innerHTML = html;
    }

    window.jumpToDate = function (date) {
        state.startDate = parseDate(date);
        state.selectedDate = date;
        document.getElementById("monthCard").classList.remove("open");

        loadOverview().catch(console.error);

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    };

    loadOverview().catch(function (error) {
        console.error(
            "Green Vita shared reservation calendar:",
            error
        );
    });

})();
</script>
