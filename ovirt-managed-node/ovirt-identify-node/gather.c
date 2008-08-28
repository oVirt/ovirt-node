
/* gather.c -- Contains methods for collecting data about the system.
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
init_gather(void)
{
    int result = 1;

    hal_ctx = get_hal_ctx();

    if (hal_ctx != NULL) {
        result = 0;
    }

    return result;
}

int
get_uuid(void)
{
    const char *udi = "/org/freedesktop/Hal/devices/computer";

    const char *key = "system.hardware.uuid";

    VERBOSE("Getting system UUID.\n");

    int result = 1;

    int type;

    type = libhal_device_get_property_type(hal_ctx, udi, key, &dbus_error);

    if (type == LIBHAL_PROPERTY_TYPE_STRING) {
        char *value;

        DEBUG("%s/%s=%d\n", udi, key, type);

        value =
            libhal_device_get_property_string(hal_ctx, udi, key,
                                              &dbus_error);
        snprintf(uuid, BUFFER_LENGTH, "%s", value);

        DEBUG("UUID=%s\n", uuid);

        result = 0;
    }

    return result;
}

/* Creates a new instance of type t_cpu_info and places it into the
 * linked list of CPUs.
 */
cpu_info_ptr
create_cpu_info(void)
{
    cpu_info_ptr result = calloc(1, sizeof(t_cpu_info));

    bzero(result, sizeof(t_cpu_info));

    strcpy(result->core_num, "0");
    strcpy(result->number_of_cores, "1");

    return result;
}

int
get_cpu_info(void)
{
    int result = 1;

    FILE *inputfd;

    cpu_info_ptr current = NULL;

    /* in order to support Xen, this data will need to be gathered
     * from libvirt rather than directly from cpuinfo
     */
    if ((inputfd = fopen("/proc/cpuinfo", "rb")) != NULL) {
        VERBOSE("Parsing CPU information\n");
        do {
            char buffer[255];

            char label[BUFFER_LENGTH];

            char value[BUFFER_LENGTH];

            fgets(buffer, 255, inputfd);
            if (strlen(buffer) > 0)
                buffer[strlen(buffer) - 1] = '\0';

            get_label_and_value(buffer,
                                label, BUFFER_LENGTH,
                                value, BUFFER_LENGTH);

            DEBUG("label=\"%s\", value=\"%s\"\n", label, value);

            if (strlen(label)) {
                if (!strcmp(label, "processor")) {
                    VERBOSE("Starting new CPU\n");

                    cpu_info_ptr last = current;

                    current = create_cpu_info();
                    if (last != NULL) {
                        last->next = current;
                    } else {
                        cpu_info = current;
                    }

                    COPY_VALUE_TO_BUFFER(value, current->cpu_num,
                                         BUFFER_LENGTH);
                } else
                    /* core id and number of cores is not correct on
                     * Xen machines
                     */
                if (!strcmp(label, "core id")) {
                    COPY_VALUE_TO_BUFFER(value, current->core_num,
                                         BUFFER_LENGTH);
                } else if (!strcmp(label, "cpu cores")) {
                    COPY_VALUE_TO_BUFFER(value, current->number_of_cores,
                                         BUFFER_LENGTH);
                } else if (!strcmp(label, "vendor_id")) {
                    COPY_VALUE_TO_BUFFER(value, current->vendor,
                                         BUFFER_LENGTH);
                } else if (!strcmp(label, "model")) {
                    COPY_VALUE_TO_BUFFER(value, current->model,
                                         BUFFER_LENGTH);
                } else if (!strcmp(label, "cpu family")) {
                    COPY_VALUE_TO_BUFFER(value, current->family,
                                         BUFFER_LENGTH);
                } else if (!strcmp(label, "cpuid level")) {
                    COPY_VALUE_TO_BUFFER(value, current->cpuid_level,
                                         BUFFER_LENGTH);
                } else if (!strcmp(label, "cpu MHz")) {
                    COPY_VALUE_TO_BUFFER(value, current->speed,
                                         BUFFER_LENGTH);
                } else if (!strcmp(label, "cache size")) {
                    COPY_VALUE_TO_BUFFER(value, current->cache,
                                         BUFFER_LENGTH);
                } else if (!strcmp(label, "flags")) {
                    COPY_VALUE_TO_BUFFER(value, current->flags,
                                         BUFFER_LENGTH);
                }
            }

        } while (!feof(inputfd));

        fclose(inputfd);

        result = 0;
    } else {
        VERBOSE("Unable to open /proc/cpuinfo\n");
    }

    return result;
}

/* Creates a new instance of type t_nic_info.
 */
nic_info_ptr
create_nic_info(void)
{
    nic_info_ptr result = calloc(1, sizeof(t_nic_info));

    bzero(result, sizeof(t_nic_info));

    return result;
}

/* Determines the speed of the network interface.
 */
void
get_nic_data(char *nic, nic_info_ptr nic_info)
{
    char *interface;

    struct ifreq ifr;

    int sockfd;

    struct ethtool_cmd ecmd;

    interface =
        libhal_device_get_property_string(hal_ctx, nic, "net.interface",
                                          &dbus_error);
    bzero(&ifr, sizeof(struct ifreq));

    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd >= 0) {
        int bandwidth;

        ifr.ifr_addr.sa_family = AF_INET;
        strncpy(ifr.ifr_name, interface, IFNAMSIZ - 1);

        ioctl(sockfd, SIOCETHTOOL, &ifr);
        close(sockfd);

        bandwidth = 10;
        if (ecmd.supported & SUPPORTED_10000baseT_Full)
            bandwidth = 10000;
        else if (ecmd.supported & SUPPORTED_2500baseX_Full)
            bandwidth = 2500;
        else if (ecmd.supported & (SUPPORTED_1000baseT_Half |
                                   SUPPORTED_1000baseT_Full))
            bandwidth = 1000;
        else if (ecmd.supported & (SUPPORTED_100baseT_Half |
                                   SUPPORTED_100baseT_Full))
            bandwidth = 100;
        else if (ecmd.supported & (SUPPORTED_10baseT_Half |
                                   SUPPORTED_10baseT_Full))
            bandwidth = 10;

        snprintf(nic_info->bandwidth, BUFFER_LENGTH, "%d", bandwidth);
    }
}

int
get_nic_info(void)
{
    int result = 0;

    nic_info_ptr current = NULL;

    nic_info_ptr last = NULL;

    char **nics;

    int num_results;

    int index;

    nics = libhal_find_device_by_capability(hal_ctx, "net",
                                            &num_results, &dbus_error);

    DEBUG("Found %d NICs\n", num_results);

    for (index = 0; index < num_results; index++) {
        char *nic = nics[index];

        VERBOSE("Starting new NIC.\n");

        if (current != NULL) {
            last = current;
            current = create_nic_info();
            last->next = current;
        } else {
            nic_info = current = create_nic_info();
        }

        snprintf(current->mac_address, BUFFER_LENGTH, "%s",
                 libhal_device_get_property_string(hal_ctx, nic,
                                                   "net.address",
                                                   &dbus_error));
        get_nic_data(nic, current);

        DEBUG("NIC details: MAC:%s, speed:%s, IP:%s\n",
              nic_info->mac_address, nic_info->bandwidth,
              nic_info->ip_address);
    }

    return result;
}
