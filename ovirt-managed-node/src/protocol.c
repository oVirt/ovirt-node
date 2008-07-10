
/* protocol.c -- Manages the communication between the managed node and
 *               the oVirt server.
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

int
create_connection(void)
{
    int result = 1;

    struct addrinfo hints;

    struct addrinfo *results;

    char port[6];

    struct addrinfo *rptr;

    VERBOSE("Creating the socket connection.\n");

    memset(&hints, 0, sizeof(struct addrinfo));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = 0;
    hints.ai_protocol = 0;

    VERBOSE("Searching for host candidates.\n");

    snprintf(port, 6, "%d", hostport);

    if (!getaddrinfo(hostname, port, &hints, &results)) {
        VERBOSE
            ("Got address information. Searching for a proper entry.\n");

        for (rptr = results; rptr != NULL; rptr = rptr->ai_next) {
            if (debug) {
                fprintf(stdout,
                        "Attempting connection: family=%d, socket type=%d, protocol=%d\n",
                        rptr->ai_family, rptr->ai_socktype,
                        rptr->ai_protocol);
            }

            socketfd =
                socket(rptr->ai_family, rptr->ai_socktype,
                       rptr->ai_protocol);

            if (socketfd == -1) {
                continue;
            }

            if (connect(socketfd, rptr->ai_addr, rptr->ai_addrlen) != -1) {
                break;
            }
            //  invalid connection, so close it
            VERBOSE("Invalid connection.\n");
            close(socketfd);
        }

        if (rptr == NULL) {
            VERBOSE("Unable to connect to server %s:%d\n", hostname,
                    hostport);
        } else {
            // success
            result = 0;
        }

        freeaddrinfo(results);
    } else {
        VERBOSE("No hosts found. Exiting...\n");
    }

    DEBUG("create_connection: result=%d\n", result);

    return result;
}

int
start_conversation(void)
{
    int result = 1;

    VERBOSE("Starting conversation with %s:%d.\n", hostname, hostport);

    if (!create_connection()) {
        VERBOSE("Connected.\n");

        if (!get_text("HELLO?")) {
            VERBOSE("Checking for handshake.\n");

            if (!send_text("HELLO!")) {
                VERBOSE("Handshake received. Starting conversation.\n");

                if (!get_text("MODE?")) {
                    VERBOSE("Shifting to IDENTIFY mode.\n");

                    if (!send_text("IDENTIFY"))
                        result = 0;
                } else {
                    VERBOSE("Was not asked for a mode.\n");
                }
            }
        } else {
            VERBOSE("Did not receive a proper handshake.\n");
        }
    }

    else {
        VERBOSE("Did not get a connection.\n");
    }

    DEBUG("start_conversation: result=%d\n", result);

    return result;
}

/* Transmits the CPU details to the server.
 */
int
send_cpu_details(void)
{
    int result = 1;

    cpu_info_ptr current = cpu_info;

    while (current != NULL) {
        send_text("CPU");

        if (!(get_text("CPUINFO?")) &&
            (!send_value("CPUNUM", current->cpu_num)) &&
            (!send_value("CORENUM", current->core_num)) &&
            (!send_value("NUMCORES", current->number_of_cores)) &&
            (!send_value("VENDOR", current->vendor)) &&
            (!send_value("MODEL", current->model)) &&
            (!send_value("FAMILY", current->family)) &&
            (!send_value("CPUIDLVL", current->cpuid_level)) &&
            (!send_value("SPEED", current->speed)) &&
            (!send_value("CACHE", current->cache)) &&
            (!send_value("FLAGS", current->flags))) {
            send_text("ENDCPU");
            result = get_text("ACK CPU");
        }

        current = current->next;
    }


    return result;
}

/* Transmits the NIC details to the server.
 */
int
send_nic_details(void)
{
    int result = 1;

    nic_info_ptr current = nic_info;

    while (current != NULL) {
        send_text("NIC");

        if (!(get_text("NICINFO?")) &&
            (!send_value("MAC", current->mac_address)) &&
            (!send_value("BANDWIDTH", current->bandwidth))) {
            send_text("ENDNIC");
            result = get_text("ACK NIC");
        }

        current = current->next;
    }

    return result;
}

int
send_details(void)
{
    int result = 1;

    VERBOSE("Sending node details.\n");

    if (!get_text("INFO?")) {
        if ((!send_value("ARCH", arch)) &&
            (!send_value("UUID", uuid)) &&
            (!send_value("MEMSIZE", memsize)) &&
            (!send_cpu_details() && !send_nic_details())) {
            if (!send_text("ENDINFO"))
                result = 0;
        }
    } else {
        VERBOSE("Was not interrogated for hardware info.\n");
    }

    return result;
}

int
end_conversation(void)
{
    int result = 0;

    VERBOSE("Ending conversation.\n");

    send_text("ENDINFO");

    close(socketfd);

    return result;
}

int
send_value(char *label, char *value)
{
    char buffer[BUFFER_LENGTH];

    int result = 1;

    char expected[BUFFER_LENGTH];

    snprintf(buffer, BUFFER_LENGTH, "%s=%s", label, value);

    if (!send_text(buffer)) {
        snprintf(expected, BUFFER_LENGTH, "ACK %s", label);

        VERBOSE("Expecting \"%s\"\n", expected);

        result = get_text(expected);
    }

    return result;
}

int
send_text(char *text)
{
    int result = 1;

    int sent;

    VERBOSE("Sending: \"%s\"\n", text);

    sent = safewrite(socketfd, text, strlen(text));
    sent += safewrite(socketfd, "\n", 1);

    if (sent >= 0) {
        DEBUG("Sent %d bytes total.\n", sent);

        result = 0;
    }

    return result;
}
