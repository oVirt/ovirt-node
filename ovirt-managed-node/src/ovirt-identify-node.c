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

#include <errno.h>
#include <getopt.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libvirt/libvirt.h>
#include <netinet/in.h>
#include <sys/types.h>
#include <sys/socket.h>

#include "ovirt-identify-node.h"

int main(int argc,char** argv)
{
    int result = 1;
    virConnectPtr connection;
    virNodeInfo info;

    fprintf(stdout,"Sending managed node details to server.\n");

    if(!config(argc,argv))
    {
        if(verbose)  fprintf(stdout,"Connecting to libvirt.\n");

        connection = virConnectOpenReadOnly(testing ? "test:///default" : NULL);

        if(debug) fprintf(stderr,"connection=%p\n",connection);

        if(connection)
        {
            if(verbose) fprintf(stdout,"Getting hostname: %s\n", uuid);
            if(!strlen(uuid)) gethostname(uuid,sizeof uuid);

            if(verbose) fprintf(stdout,"Retrieving node information.\n");
            if(!virNodeGetInfo(connection,&info))
            {
                snprintf(arch, BUFFER_LENGTH, "%s", info.model);
                snprintf(memsize, BUFFER_LENGTH, "%ld", info.memory);

                cpu_info = NULL;

                if(!get_cpu_info())
                {
                    if(verbose) fprintf(stdout, "Getting CPU info.\n");

                    if(debug)
                    {
                        fprintf(stdout,"Node Info:\n");
                        fprintf(stdout,"     UUID: %s\n", uuid);
                        fprintf(stdout,"     Arch: %s\n", arch);
                        fprintf(stdout,"   Memory: %s\n", memsize);

                        t_cpu_info* current = cpu_info;
                        while(current != NULL)
                        {
                            fprintf(stdout,"\n");
                            fprintf(stdout,"     CPU Number: %s\n", current->cpu_num);
                            fprintf(stdout,"    Core Number: %s\n", current->core_num);
                            fprintf(stdout,"Number of Cores: %s\n", current->number_of_cores);
                            fprintf(stdout,"         Vendor: %s\n", current->vendor);
                            fprintf(stdout,"          Model: %s\n", current->model);
                            fprintf(stdout,"         Family: %s\n", current->family);
                            fprintf(stdout,"    CPUID Level: %s\n", current->cpuid_level);
                            fprintf(stdout,"      CPU Speed: %s\n", current->speed);
                            fprintf(stdout,"     Cache Size: %s\n", current->cache);
                            fprintf(stdout,"      CPU Flags: %s\n", current->flags);

                            current = current->next;
                        }
                    }

                    if(verbose) fprintf(stdout, "Retrieved node information.\n");

                    if(!start_conversation() && !send_details() && !end_conversation())
                    {
                        fprintf(stdout,"Finished!\n");
                        result = 0;
                    }
                }
                else
                {
                    if(verbose) fprintf(stderr,"Failed to get CPU info.\n");
                }
            }
            else
            {
                if(verbose) fprintf(stderr,"Failed to get node info.\n");
            }
        }
        else
        {
            if(verbose) fprintf(stderr,"Could not connect to libvirt.\n");
        }
    }
    else
    {
        usage();
    }

    return result;
}

int config(int argc,char** argv)
{
    int result = 0;
    int option;

    while((option = getopt(argc,argv,"s:p:u:dvth")) != -1)
    {
        if(debug) fprintf(stdout,"Processing argument: %c (optarg:%s)\n",option,optarg);

        switch(option)
        {
            case 's': hostname = optarg; break;
            case 'p': hostport = atoi(optarg); break;
            case 'u': snprintf(uuid,VIR_UUID_BUFLEN,"%s",optarg); break;
            case 't': testing  = 1; break;
            case 'd': debug    = 1; break;
            case 'v': verbose  = 1; break;
            case 'h':
            // fall thru
            default : result   = 1; break;
        }
    }

    // verify that required options are provided
    if(hostname == NULL || strlen(hostname) == 0)
    {
        fprintf(stderr,"ERROR: The server name is required. (-s [hostname])\n");
        result = 1;
    }

    if(hostport <= 0)
    {
        fprintf(stderr,"ERROR: The server port is required. (-p [port])\n");
        result = 1;
    }

    return result;
}

void usage()
{
    fprintf(stdout,"\n");
    fprintf(stdout,"Usage: ovirt-identify [OPTION]\n");
    fprintf(stdout,"\n");
    fprintf(stdout,"\t-s [server]\t\tThe remote server's hostname.\n");
    fprintf(stdout,"\t-p [port]\t\tThe remote server's port.\n");
    fprintf(stdout,"\t-d\t\tDisplays debug information during execution.\n");
    fprintf(stdout,"\t-v\t\tDisplays verbose information during execution.\n");
    fprintf(stdout,"\t-h\t\tDisplays this help information and then exits.\n");
    fprintf(stdout,"\n");
}

int start_conversation(void)
{
    int result = 1;

    if(verbose || debug) fprintf(stdout,"Starting conversation with %s:%d.\n",hostname,hostport);

    if(!create_connection())
    {
        if(debug || verbose) fprintf(stdout,"Connected.\n");

        if (!get_text("HELLO?"))
        {
            if(verbose) fprintf(stdout,"Checking for handshake.\n");

            if(!send_text("HELLO!"))
            {
                if(verbose) fprintf(stdout,"Handshake received. Starting conversation.\n");

                if(!get_text("MODE?"))
                {
                    if(verbose) fprintf(stdout,"Shifting to IDENTIFY mode.\n");

                    if(!send_text("IDENTIFY")) result = 0;
                }
                else
                {
                    if(verbose) fprintf(stderr,"Was not asked for a mode.\n");
                }
            }
        }
        else
        {
            if(verbose) fprintf(stderr,"Did not receive a proper handshake.\n");
        }
    }

    else
    {
        if(verbose) fprintf(stderr,"Did not get a connection.\n");
    }

    if(debug) fprintf(stdout,"start_conversation: result=%d\n", result);

    return result;
}

int send_value(char* label,char* value)
{
    char buffer[BUFFER_LENGTH];
    int result = 1;
    char expected[BUFFER_LENGTH];

    snprintf(buffer,BUFFER_LENGTH,"%s=%s", label, value);

    if(!send_text(buffer))
    {
        snprintf(expected, BUFFER_LENGTH, "ACK %s", label);

        if(verbose) fprintf(stdout,"Expecting \"%s\"\n", expected);

        result = get_text(expected);
    }

    return result;
}

int send_details(void)
{
    int result = 1;

    if(verbose) fprintf(stdout,"Sending node details.\n");

    if (!get_text("INFO?"))
    {
        if((!send_value("ARCH",     arch))     &&
           (!send_value("UUID",     uuid))     &&
           (!send_value("MEMSIZE",  memsize))  &&
           (!send_cpu_details()))
        {
            if(!send_text("ENDINFO")) result = 0;
        }
    }
    else
    {
        if(verbose) fprintf(stdout,"Was not interrogated for hardware info.\n");
    }

    return result;
}

int send_cpu_details(void)
{
    int result = 1;
    t_cpu_info* current = cpu_info;

    while(current != NULL)
    {
        send_text("CPU");

        if(!(get_text("CPUINFO?"))                              &&
           (!send_value("CPUNUM",current->cpu_num))             &&
           (!send_value("CORENUM",current->core_num))           &&
           (!send_value("NUMCORES",current->number_of_cores))   &&
           (!send_value("VENDOR",current->vendor))              &&
           (!send_value("MODEL",current->model))                &&
           (!send_value("FAMILY",current->family))              &&
           (!send_value("CPUIDLVL",current->cpuid_level))       &&
           (!send_value("SPEED",current->speed))                &&
           (!send_value("CACHE", current->cache))               &&
           (!send_value("FLAGS", current->flags)))
            {
                send_text("ENDCPU");
                result = get_text("ACK CPU");
            }

        current = current->next;
    }


    return result;
}

int end_conversation(void)
{
    int result = 0;

    if(debug || verbose) fprintf(stdout,"Ending conversation.\n");

    send_text("ENDINFO");

    close(socketfd);

    return result;
}

void get_label_and_value(char* text,
                         char* label, size_t label_length,
                         char* value, size_t value_length)
{
    int   offset  = 0;
    int   which   = 0; /* 0 = label, 1 = value */
    char* current = text;

    /* iterate through the text supplied and find where the
     * label ends with a colon, then copy that into the supplied
     * label buffer and trim any trailing spaces
     */

    while(current != NULL && *current != '\0')
    {
        /* if we're on the separator, then switch modes and reset
         * the offset indicator, otherwise just process the character
         */
        if(which == 0 && *current == ':')
        {
            which  = 1;
            offset = 0;
        }
        else
        {
            char* buffer = (which == 0 ? label : value);
            int   length = (which == 0 ? label_length : value_length);

            /* only copy if we're past the first character and it's not
             * a space
             */
            if((offset > 0 || (*current != 9 && *current != ' ')) && offset < (length - 1))
            {
                buffer[offset++] = *current;
                buffer[offset]   = 0;
            }
        }

        current++;
    }

    /* now trim all trailing spaces from the values */
    while(label[strlen(label) - 1 ] == 9)
        label[strlen(label) - 1] = 0;
    while(value[strlen(value) - 1] == 9)
        value[strlen(value) - 1] = 0;
}

int get_cpu_info(void)
{
    int result = 1;
    FILE* inputfd;
    t_cpu_info* current = NULL;

    if(( inputfd = fopen("/proc/cpuinfo","rb")) != NULL)
    {
        if(verbose) fprintf(stdout,"Parsing CPU information\n");
        do
        {
            char buffer[255];
            char label[BUFFER_LENGTH];
            char value[BUFFER_LENGTH];

            fgets(buffer, 255, inputfd);
            if(strlen(buffer) > 0) buffer[strlen(buffer) - 1] = '\0';

            get_label_and_value(buffer,
                                label,BUFFER_LENGTH,
                                value,BUFFER_LENGTH);

            if(debug)
                fprintf(stdout,"label=\"%s\", value=\"%s\"\n", label, value);

            if(strlen(label))
            {
                if(!strcmp(label,"processor"))
                {
                    if(debug || verbose)
                        fprintf(stdout,"Starting new CPU\n");

                    t_cpu_info* last = current;

                    current = create_cpu_info();
                    if(last != NULL)
                    {
                        last->next = current;
                    }
                    else
                    {
                        cpu_info = current;
                    }

                    COPY_VALUE_TO_BUFFER(value,current->cpu_num,BUFFER_LENGTH);
                }
                else
                if(!strcmp(label,"core id"))
                {
                    COPY_VALUE_TO_BUFFER(value,current->core_num,BUFFER_LENGTH);
                }
                else
                if(!strcmp(label,"cpu cores"))
                {
                    COPY_VALUE_TO_BUFFER(value,current->number_of_cores,BUFFER_LENGTH);
                }
                else
                if(!strcmp(label,"vendor_id"))
                {
                    COPY_VALUE_TO_BUFFER(value,current->vendor,BUFFER_LENGTH);
                }
                else
                if(!strcmp(label,"model"))
                {
                    COPY_VALUE_TO_BUFFER(value,current->model,BUFFER_LENGTH);
                }
                else
                if(!strcmp(label,"cpu family"))
                {
                    COPY_VALUE_TO_BUFFER(value,current->family,BUFFER_LENGTH);
                }
                else
                if(!strcmp(label,"cpuid level"))
                {
                    COPY_VALUE_TO_BUFFER(value,current->cpuid_level,BUFFER_LENGTH);
                }
                else
                if(!strcmp(label,"cpu MHz"))
                {
                    COPY_VALUE_TO_BUFFER(value,current->speed,BUFFER_LENGTH);
                }
                else
                if(!strcmp(label,"cache size"))
                {
                    COPY_VALUE_TO_BUFFER(value,current->cache,BUFFER_LENGTH);
                }
                else
                if(!strcmp(label,"flags"))
                {
                    COPY_VALUE_TO_BUFFER(value,current->flags,BUFFER_LENGTH);
                }
            }

        } while(!feof(inputfd));

        fclose(inputfd);

        result = 0;
    }
    else
    {
        if(verbose) fprintf(stderr,"Unable to open /proc/cpuinfo\n");
    }

    return result;
}

t_cpu_info* create_cpu_info(void)
{
    t_cpu_info* result = calloc(1,sizeof(t_cpu_info));
    bzero(result,sizeof(t_cpu_info));

    strcpy(result->core_num,"0");
    strcpy(result->number_of_cores,"1");


    return result;
}

ssize_t safewrite(int fd, const void *buf, size_t count)
{
        size_t nwritten = 0;
        while (count > 0) {
                ssize_t r = write(fd, buf, count);

                if (r < 0 && errno == EINTR)
                        continue;
                if (r < 0)
                        return r;
                if (r == 0)
                        return nwritten;
                buf = (const char *)buf + r;
                count -= r;
                nwritten += r;
        }
        return nwritten;
}

int send_text(char* text)
{
    int result = 1;
    int sent;

    if(verbose) fprintf(stdout,"Sending: \"%s\"\n", text);

    sent = safewrite(socketfd, text, strlen(text));
    sent += safewrite(socketfd, "\n", 1);

    if(sent >= 0)
    {
        if(debug) fprintf(stdout,"Sent %d bytes total.\n", sent);

        result = 0;
    }

    return result;
}

int saferead(int fd, char *buf, size_t count)
{
    ssize_t bytes,offset;
    int len_left;
    int done = 0;

    if(debug) fprintf(stdout,"Begin saferead(%d, %p, %ld)\n", fd, buf, count);

    offset = 0;
    len_left = count;


    while(!done)
    {
        if(debug) fprintf(stdout,"Before read(%ld,%p,%ld)\n",fd,buf+offset,len_left);

        bytes = read(fd, buf+offset, len_left);

        if(debug) fprintf(stdout,"After read: bytes=%ld\n", bytes);

        if(bytes == 0)
        {
            done = 1;
        }
        else if(bytes > 0)
        {
            offset += bytes;
            len_left -= bytes;
            done = 1;
        }
        else if(errno == EINTR)
        {
            continue;
        }
        else
        {
            done = 1;
        }

        if(debug) fprintf(stdout,"End of decision loop: offset=%ld, len_left=%dl, done=%d\n",offset, len_left, done);
    }

    return offset;
}

int get_text(const char *const expected)
{
    int result = 1;
    int received;
    char buffer[BUFFER_LENGTH];
    bzero(buffer,BUFFER_LENGTH);

    if(verbose) fprintf(stdout, "Looking to receive %s\n", expected);

    received = saferead(socketfd, buffer, BUFFER_LENGTH);

    buffer[received - 1] = 0;

    if(verbose) fprintf(stdout,"Received \"%s\": size=%d (trimmed ending carriage return)\n", buffer, received);

    result = strcmp(expected,buffer);

    return result;
}

int create_connection(void)
{
    int result = 1;
    struct addrinfo hints;
    struct addrinfo* results;
    char port[6];
    struct addrinfo* rptr;

    if(verbose) fprintf(stdout,"Creating the socket connection.\n");

    memset(&hints, 0, sizeof(struct addrinfo));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = 0;
    hints.ai_protocol = 0;

    if(verbose) fprintf(stdout,"Searching for host candidates.\n");

    snprintf(port, 6, "%d", hostport);

    if(!getaddrinfo(hostname, port, &hints, &results))
    {
        if(verbose) fprintf(stdout,"Got address information. Searching for a proper entry.\n");

        for(rptr = results; rptr != NULL; rptr = rptr->ai_next)
        {
            if(debug)
            {
                fprintf(stdout,"Attempting connection: family=%d, socket type=%d, protocol=%d\n",
                rptr->ai_family, rptr->ai_socktype, rptr->ai_protocol);
            }

            socketfd = socket(rptr->ai_family, rptr->ai_socktype, rptr->ai_protocol);

            if(socketfd == -1)
            {
                continue;
            }

            if(connect(socketfd, rptr->ai_addr, rptr->ai_addrlen) != -1)
            {
                break;
            }

            //  invalid connection, so close it
            if(verbose) fprintf(stdout, "Invalid connection.\n");
            close(socketfd);
        }

        if(rptr == NULL)
        {
            if(verbose) fprintf(stdout,"Unable to connect to server %s:%d\n", hostname, hostport);
        }
        else
        {
            // success
            result = 0;
        }

        freeaddrinfo(results);
    }
    else
    {
        if(verbose) fprintf(stderr,"No hosts found. Exiting...\n");
    }

    if(debug) fprintf(stdout, "create_connection: result=%d\n", result);

    return result;
}
