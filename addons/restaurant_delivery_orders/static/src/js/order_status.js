(function () {
    "use strict";

    function shouldRunOnOrderDetailPage() {
        return /^\/casavieja\/mis-pedidos\/\d+\/?$/.test(window.location.pathname);
    }

    function renderStatus(container, stateLabel, badgeClass) {
        container.innerHTML = "";
        var badge = document.createElement("span");
        badge.className = "badge fs-6 " + (badgeClass || "bg-secondary");
        badge.textContent = stateLabel || "";
        container.appendChild(badge);
    }

    function initOrderStatusPolling() {
        if (!shouldRunOnOrderDetailPage()) {
            return;
        }

        var container = document.getElementById("order-status");
        if (!container) {
            return;
        }

        var orderId = container.dataset.orderId;
        if (!orderId) {
            return;
        }

        var intervalId = null;

        function poll() {
            fetch("/casavieja/api/order-status/" + orderId, {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
                credentials: "same-origin",
            })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error("status_fetch_failed");
                    }
                    return response.json();
                })
                .then(function (data) {
                    renderStatus(container, data.state_label, data.badge_class);
                    if (data.state === "delivered" || data.state === "cancelled") {
                        if (intervalId) {
                            clearInterval(intervalId);
                        }
                    }
                })
                .catch(function () {
                    // Keep polling on transient errors.
                });
        }

        poll();
        intervalId = setInterval(poll, 30000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initOrderStatusPolling);
    } else {
        initOrderStatusPolling();
    }
})();
