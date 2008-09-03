/* Copyright (C) 2008 Red Hat, Inc.
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

#ifndef __OVIRT_IDENTIFY_NODE_H
#define __OVIRT_IDENTIFY_NODE_H

#include <errno.h>
#include <getopt.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <arpa/inet.h>

#include <hal/libhal.h>

#include <libvirt/libvirt.h>

#include <linux/ethtool.h>
#include <linux/sockios.h>
#include <linux/if.h>

#include <netinet/in.h>

#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/socket.h>

#define BUFFER_LENGTH 128
#define CPU_FLAGS_BUFFER_LENGTH 256

typedef struct _cpu_info {
    char cpu_num[BUFFER_LENGTH];
    char core_num[BUFFER_LENGTH];
    char number_of_cores[BUFFER_LENGTH];
    char vendor[BUFFER_LENGTH];
    char model[BUFFER_LENGTH];
    char family[BUFFER_LENGTH];
    char cpuid_level[BUFFER_LENGTH];
    char speed[BUFFER_LENGTH];
    char cache[BUFFER_LENGTH];
    char flags[CPU_FLAGS_BUFFER_LENGTH];
    struct _cpu_info* next;
} t_cpu_info;

typedef t_cpu_info* cpu_info_ptr;

typedef struct _nic_info {
    char mac_address[BUFFER_LENGTH];
    char bandwidth[BUFFER_LENGTH];
    char ip_address[BUFFER_LENGTH];
    struct _nic_info* next;
} t_nic_info;

typedef t_nic_info* nic_info_ptr;

int  config(int argc,char** argv);
void usage(void);

void get_label_and_value(char* text,
                         char* label,size_t label_length,
                         char* value,size_t value_length);

int send_text(char* text);
int get_text(const char *const expected);

/* comm.c */
ssize_t saferead(int fd, char *buf, size_t count);
ssize_t safewrite(int fd, const void *buf, size_t count);

/* debug.c */
void debug_cpu_info(void);

/* gather.c */
int init_gather(void);
int get_uuid(void);
int get_cpu_info(void);
int get_nic_info(void);

/* hal_support.c */
LibHalContext* get_hal_ctx(void);

/* protocol.c */
int create_connection(void);
int start_conversation(void);
int send_details(void);
int end_conversation(void);
int send_value(char* label,char* value);
int send_text(char* text);

/* variables */
extern int  debug;
extern int  verbose;
extern int  testing;

extern char arch[BUFFER_LENGTH];
extern char uuid[BUFFER_LENGTH];
extern char memsize[BUFFER_LENGTH];
extern char numcpus[BUFFER_LENGTH];
extern char cpuspeed[BUFFER_LENGTH];
extern char *hostname;
extern int  hostport;
extern int  socketfd;
extern cpu_info_ptr cpu_info;
extern nic_info_ptr nic_info;

extern DBusConnection* dbus_connection;
extern DBusError       dbus_error;
extern LibHalContext*  hal_ctx;

/* macros */
#define DEBUG(arg...)   if(debug)   fprintf(stderr, ##arg)
#define VERBOSE(arg...) if(verbose) fprintf(stdout, ##arg)
#define COPY_VALUE_TO_BUFFER(value,buffer,length) \
    snprintf(buffer,length,"%s",value)

#endif
