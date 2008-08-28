
/* identify-node -- Main entry point for the identify-node utility.
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

int debug = 0;

int verbose = 0;

int testing = 0;

char arch[BUFFER_LENGTH];

char uuid[BUFFER_LENGTH];

char memsize[BUFFER_LENGTH];

char numcpus[BUFFER_LENGTH];

char cpuspeed[BUFFER_LENGTH];

char *hostname;

int hostport = -1;

int socketfd;

cpu_info_ptr cpu_info;

nic_info_ptr nic_info;

LibHalContext *hal_ctx;

int
main(int argc, char **argv)
{
    int result = 1;

    virConnectPtr connection;

    virNodeInfo info;

    fprintf(stdout, "Sending managed node details to server.\n");

    if (!config(argc, argv)) {
        VERBOSE("Connecting to libvirt.\n");

        connection =
            virConnectOpenReadOnly(testing ? "test:///default" : NULL);

        DEBUG("connection=%p\n", connection);

        if (connection) {
            VERBOSE("Retrieving node information.\n");
            if (!virNodeGetInfo(connection, &info)) {
                snprintf(arch, BUFFER_LENGTH, "%s", info.model);
                snprintf(memsize, BUFFER_LENGTH, "%ld", info.memory);

                cpu_info = NULL;
                nic_info = NULL;

                if (!init_gather() && !get_uuid() && !get_cpu_info()
                    && !get_nic_info()) {
                    if (!start_conversation() && !send_details()
                        && !end_conversation()) {
                        fprintf(stdout, "Finished!\n");
                        result = 0;
                    }
                } else {
                    VERBOSE("Failed to get CPU info.\n");
                }
            } else {
                VERBOSE("Failed to get node info.\n");
            }
        } else {
            VERBOSE("Could not connect to libvirt.\n");
        }
    } else {
        usage();
    }

    return result;
}

int
config(int argc, char **argv)
{
    int result = 0;

    int option;

    while ((option = getopt(argc, argv, "s:p:dvth")) != -1) {
        DEBUG("Processing argument: %c (optarg:%s)\n", option, optarg);

        switch (option) {
            case 's':
                hostname = optarg;
                break;
            case 'p':
                hostport = atoi(optarg);
                break;
            case 't':
                testing = 1;
                break;
            case 'd':
                debug = 1;
                break;
            case 'v':
                verbose = 1;
                break;
            case 'h':
                // fall thru
            default:
                result = 1;
                break;
        }
    }

    // verify that required options are provided
    if (hostname == NULL || strlen(hostname) == 0) {
        fprintf(stderr,
                "ERROR: The server name is required. (-s [hostname])\n");
        result = 1;
    }

    if (hostport <= 0) {
        fprintf(stderr,
                "ERROR: The server port is required. (-p [port])\n");
        result = 1;
    }

    return result;
}

void
usage()
{
    fprintf(stdout, "\n");
    fprintf(stdout, "Usage: ovirt-identify [OPTION]\n");
    fprintf(stdout, "\n");
    fprintf(stdout, "\t-s [server]\t\tThe remote server's hostname.\n");
    fprintf(stdout, "\t-p [port]\t\tThe remote server's port.\n");
    fprintf(stdout,
            "\t-d\t\tDisplays debug information during execution.\n");
    fprintf(stdout,
            "\t-v\t\tDisplays verbose information during execution.\n");
    fprintf(stdout,
            "\t-h\t\tDisplays this help information and then exits.\n");
    fprintf(stdout, "\n");
}

void
get_label_and_value(char *text,
                    char *label, size_t label_length,
                    char *value, size_t value_length)
{
    int offset = 0;

    int which = 0;              /* 0 = label, 1 = value */

    char *current = text;

    /* iterate through the text supplied and find where the
     * label ends with a colon, then copy that into the supplied
     * label buffer and trim any trailing spaces
     */

    while (current != NULL && *current != '\0') {
        /* if we're on the separator, then switch modes and reset
         * the offset indicator, otherwise just process the character
         */
        if (which == 0 && *current == ':') {
            which = 1;
            offset = 0;
        } else {
            char *buffer = (which == 0 ? label : value);

            int length = (which == 0 ? label_length : value_length);

            /* only copy if we're past the first character and it's not
             * a space
             */
            if ((offset > 0 || (*current != 9 && *current != ' '))
                && offset < (length - 1)) {
                buffer[offset++] = *current;
                buffer[offset] = 0;
            }
        }

        current++;
    }

    /* now trim all trailing spaces from the values */
    while (label[strlen(label) - 1] == 9)
        label[strlen(label) - 1] = 0;
    while (value[strlen(value) - 1] == 9)
        value[strlen(value) - 1] = 0;
}

int
get_text(const char *const expected)
{
    int result = 1;

    int received;

    char buffer[BUFFER_LENGTH];

    bzero(buffer, BUFFER_LENGTH);

    VERBOSE("Looking to receive %s\n", expected);

    received = saferead(socketfd, buffer, BUFFER_LENGTH);

    buffer[received - 1] = 0;

    VERBOSE("Received \"%s\": size=%d (trimmed ending carriage return)\n",
            buffer, received);

    result = strcmp(expected, buffer);

    return result;
}
