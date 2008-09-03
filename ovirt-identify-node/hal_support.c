
/* hal_support.c -- Interfaces with the HAL libraries.
 *
 * Copyright (C) 2008 Red Hat, Inc.
 * Written by Darryl L. Pierce <dpierce@redhat.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 2 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
 * MA  02110-1301, USA.  A copy of the GNU General Public License is
 * also available at http://www.gnu.org/copyleft/gpl.html.
 */

#include "ovirt-identify-node.h"

DBusConnection *dbus_connection;

DBusError dbus_error;

LibHalContext *
get_hal_ctx(void)
{
    LibHalContext *result = NULL;

    LibHalContext *ctx;

    ctx = libhal_ctx_new();
    if (ctx != NULL) {
        dbus_error_init(&dbus_error);
        dbus_connection = dbus_bus_get(DBUS_BUS_SYSTEM, &dbus_error);

        if (!dbus_error_is_set(&dbus_error)) {
            libhal_ctx_set_dbus_connection(ctx, dbus_connection);

            if (libhal_ctx_init(ctx, &dbus_error)) {
                result = ctx;
            } else {
                fprintf(stderr,
                        "Failed to initial libhal context: %s : %s\n",
                        dbus_error.name, dbus_error.message);
            }
        } else {
            fprintf(stderr, "Unable to connect to system bus: %s : %s\n",
                    dbus_error.name, dbus_error.message);
            dbus_error_free(&dbus_error);
        }
    } else {
        fprintf(stderr, "Unable to initialize HAL context.\n");
    }

    return result;
}
