/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        const reservationId =
            vals?.cv_reservation_id ||
            vals?.reservation_id?.id ||
            vals?.reservation_id?.[0] ||
            this.cv_reservation_id ||
            false;
        const reservationName =
            vals?.cv_reservation_name ||
            vals?.reservation_id?.name ||
            vals?.reservation_id?.[1] ||
            this.cv_reservation_name ||
            "";
        this.cv_reservation_id = reservationId;
        this.cv_reservation_name = reservationName;
    },

    setCvReservation(reservation) {
        this.cv_reservation_id = reservation?.id || false;
        this.cv_reservation_name = reservation?.name || "";
    },

    clearCvReservation() {
        this.cv_reservation_id = false;
        this.cv_reservation_name = "";
    },

    serialize() {
        const data = super.serialize ? super.serialize(...arguments) : {};
        data.cv_reservation_id = this.cv_reservation_id || false;
        data.cv_reservation_name = this.cv_reservation_name || "";
        return data;
    },

    export_for_printing() {
        const data = super.export_for_printing(...arguments);
        if (this.cv_reservation_name) {
            data.cv_reservation_name = this.cv_reservation_name;
        }
        return data;
    },
});

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    get cvReservationButtonLabel() {
        const order = this.pos.get_order();
        if (order?.cv_reservation_name) {
            return `${_t("Reserva")}: ${order.cv_reservation_name}`;
        }
        return _t("Vincular reserva");
    },

    _normalizePopupPayload(payload) {
        if (payload === undefined) {
            return undefined;
        }
        if (payload && payload.confirmed !== undefined) {
            return payload.confirmed ? payload.payload : undefined;
        }
        return payload;
    },

    async onClickCvSelectReservation() {
        const order = this.pos.get_order();
        if (!order) {
            return;
        }

        let reservations;
        try {
            reservations = await this.orm.call(
                "restaurant.table.reservation",
                "get_active_reservations_for_pos",
                [this.pos.company?.id || false],
                {
                    limit: 50,
                }
            );
        } catch (_error) {
            this.notification.add(
                _t("No se pudo consultar la lista de reservas activas."),
                { type: "danger" }
            );
            return;
        }

        if (!reservations?.length) {
            this.notification.add(_t("No hay reservas activas disponibles."), {
                type: "warning",
            });
            return;
        }

        const list = [
            {
                id: 0,
                label: _t("Quitar reserva vinculada"),
                isSelected: !order.cv_reservation_id,
                item: false,
            },
        ];
        for (const reservation of reservations) {
            list.push({
                id: reservation.id,
                label: `${reservation.name} - ${reservation.table_name} - ${reservation.start_datetime}`,
                isSelected: order.cv_reservation_id === reservation.id,
                item: reservation,
            });
        }

        const rawPayload = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Vincular reserva"),
            list,
        });
        const payload = this._normalizePopupPayload(rawPayload);
        if (payload === undefined) {
            return;
        }

        if (!payload) {
            order.clearCvReservation();
            this.notification.add(_t("Reserva desvinculada del pedido POS."), {
                type: "info",
            });
            return;
        }

        order.setCvReservation(payload);
        this.notification.add(_t("Reserva vinculada al pedido POS."), {
            type: "success",
        });
    },
});
