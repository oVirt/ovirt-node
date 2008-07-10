
/* debug.c -- Debugging methods.
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

void
debug_cpu_info(void)
{
    fprintf(stdout, "Node Info:\n");
    fprintf(stdout, "     UUID: %s\n", uuid);
    fprintf(stdout, "     Arch: %s\n", arch);
    fprintf(stdout, "   Memory: %s\n", memsize);

    cpu_info_ptr current = cpu_info;

    while (current != NULL) {
        fprintf(stdout, "\n");
        fprintf(stdout, "     CPU Number: %s\n", current->cpu_num);
        fprintf(stdout, "    Core Number: %s\n", current->core_num);
        fprintf(stdout, "Number of Cores: %s\n", current->number_of_cores);
        fprintf(stdout, "         Vendor: %s\n", current->vendor);
        fprintf(stdout, "          Model: %s\n", current->model);
        fprintf(stdout, "         Family: %s\n", current->family);
        fprintf(stdout, "    CPUID Level: %s\n", current->cpuid_level);
        fprintf(stdout, "      CPU Speed: %s\n", current->speed);
        fprintf(stdout, "     Cache Size: %s\n", current->cache);
        fprintf(stdout, "      CPU Flags: %s\n", current->flags);

        current = current->next;
    }
}
