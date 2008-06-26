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

int  config(int argc,char** argv);
void usage(void);

int start_conversation(void);
int send_details(void);
int end_conversation(void);

int send_text(char* text);
int get_text(const char *const expected);
int create_connection(void);

int debug   = 1;
int verbose = 1;
int testing = 0;

#define BUFFER_LENGTH 128

char arch[BUFFER_LENGTH];
char uuid[VIR_UUID_BUFLEN];
char memsize[BUFFER_LENGTH];
char numcpus[BUFFER_LENGTH];
char cpuspeed[BUFFER_LENGTH];
char *hostname;
int  hostport = -1;
int  socketfd;

int main(int argc,char** argv)
{
    int result = 1;
    virConnectPtr connection;
    virNodeInfo info;

    if(!config(argc,argv))
    {
        fprintf(stdout,"Connecting to libvirt.\n");

        connection = virConnectOpenReadOnly(testing ? "test:///default" : NULL);

        if(debug) fprintf(stderr,"connection=%p\n",connection);

        if(connection)
        {
            if(debug) fprintf(stdout,"Getting hostname: %s\n", uuid);
            if(!strlen(uuid)) gethostname(uuid,sizeof uuid);

            if(debug) fprintf(stdout,"Retrieving node information.\n");
            if(!virNodeGetInfo(connection,&info))
            {
                snprintf(arch, BUFFER_LENGTH, "%s", info.model);
                snprintf(memsize, BUFFER_LENGTH, "%ld", info.memory);
                snprintf(numcpus, BUFFER_LENGTH, "%d", info.cpus);
                snprintf(cpuspeed, BUFFER_LENGTH, "%d",  info.mhz);

                if(debug)
                {
                    fprintf(stdout,"Node Info:\n");
                    fprintf(stdout,"     UUID: %s\n", uuid);
                    fprintf(stdout,"     Arch: %s\n", arch);
                    fprintf(stdout,"   Memory: %s\n", memsize);
                    fprintf(stdout,"   # CPUs: %s\n", numcpus);
                    fprintf(stdout,"CPU Speed: %s\n", cpuspeed);
                }

                if(debug) fprintf(stdout, "Retrieved node information.\n");

                if(!start_conversation() && !send_details() && !end_conversation())
                {
                    result = 0;
                }
            }
            else
            {
                if(debug) fprintf(stderr,"Failed to get node info.\n");
            }
        }
        else
        {
            if(debug) fprintf(stderr,"Could not connect to libvirt.\n");
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

        if (!get_text("HELLO?\n"))
        {
            if(debug) fprintf(stdout,"Checking for handshake.\n");

            if(!send_text("HELLO!\n"))
            {
                if(debug) fprintf(stdout,"Handshake received. Starting conversation.\n");

                if(!get_text("MODE?\n"))
                {
                    if(debug) fprintf(stdout,"Shifting to IDENTIFY mode.\n");

                    if(!send_text("IDENTIFY\n")) result = 0;
                }
                else
                {
                    if(debug) fprintf(stderr,"Was not asked for a mode.\n");
                }
            }
        }
        else
        {
            if(debug) fprintf(stderr,"Did not receive a proper handshake.\n");
        }
    }

    else
    {
        if(debug) fprintf(stderr,"Did not get a connection.\n");
    }

    if(debug) fprintf(stdout,"start_conversation: result=%d\n", result);

    return result;
}

int send_value(char* label,char* value)
{
    char buffer[BUFFER_LENGTH];
    int result = 1;
    char expected[BUFFER_LENGTH];

    snprintf(buffer,BUFFER_LENGTH,"%s=%s\n", label, value);

    if(!send_text(buffer))
    {
        snprintf(expected, BUFFER_LENGTH, "ACK %s\n", label);

        if(debug) fprintf(stdout,"Expecting \"%s\"\n", expected);

        if (!get_text(expected))
        {
            result = 0;
        }

    }

    return result;
}

int send_details(void)
{
    int result = 1;

    fprintf(stdout,"Sending node details.\n");

    if (!get_text("INFO?\n"))
    {
        if((!send_value("ARCH",     arch))     &&
           (!send_value("UUID",     uuid))     &&
           (!send_value("NUMCPUS",  numcpus))  &&
           (!send_value("CPUSPEED", cpuspeed)) &&
           (!send_value("MEMSIZE",  memsize)))
        {
            if(!send_text("ENDINFO\n")) result = 0;
        }
    }
    else
    {
        if(debug) fprintf(stdout,"Was not interrogated for hardware info.\n");
    }

    return result;
}

int end_conversation(void)
{
    int result = 0;

    fprintf(stdout,"Ending conversation.\n");

    send_text("ENDINFO\n");

    close(socketfd);

    return result;
}

ssize_t safewrite(int fd, const void *buf, size_t count)
{
        size_t nwritten = 0;
        while (count > 0) {
                ssize_t r = write(fd, buf+nwritten, count);

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

    if(debug || verbose) fprintf(stdout,"\"%s\" -> %s:%d\n", text, hostname, hostport);

    sent = safewrite(socketfd, text, strlen(text));

    if(sent >= 0)
    {
        if(debug) fprintf(stdout,"Sent %d bytes total.\n", sent);

        result = 0;
    }

    return result;
}

int saferead(int fd, void *buf, size_t count)
{
    ssize_t bytes,offset;
    int len_left;

    if(debug) fprintf(stdout,"Begin saferead(%d, %p, %ld)\n", fd, buf, count);

    offset = 0;
    len_left = count;

    while(len_left > 0) {
      bytes = read(fd, buf+offset, len_left);
      fprintf(stderr,"After read, bytes is %ld\n",bytes);
      if (bytes < 0) {
	if (errno == EINTR) {
	  continue;
	}
	else {
	  offset = -1;
	  break;
	}
      }
      else if (bytes == 0) {
	// reached EOF; break out of here
	break;
      }

      offset += bytes;
      len_left -= bytes;
    }

    return offset;
}

int get_text(const char *const expected)
{
    int received;
    char buffer[BUFFER_LENGTH];

    if(debug) fprintf(stdout, "Looking to receive %s\n", expected);

    received = saferead(socketfd, buffer, strlen(expected));

    buffer[received - 1] = 0;

    if(debug) fprintf(stdout,"Received \"%s\": size=%d (trimmed ending carriage return)\n", buffer, received);

    if (strncmp(expected, buffer, strlen(expected)) != 0) {
      return 0;
    }

    return 1;
}

int create_connection(void)
{
    int result = 1;
    struct addrinfo hints;
    struct addrinfo* results;
    char port[6];
    struct addrinfo* rptr;

    if(debug) fprintf(stdout,"Creating the socket connection.\n");

    memset(&hints, 0, sizeof(struct addrinfo));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = 0;
    hints.ai_protocol = 0;

    if(debug) fprintf(stdout,"Searching for host candidates.\n");

    snprintf(port, 6, "%d", hostport);

    if(!getaddrinfo(hostname, port, &hints, &results))
    {
        if(debug) fprintf(stdout,"Got address information. Searching for a proper entry.\n");

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
            if(debug) fprintf(stdout, "Invalid connection.\n");
            close(socketfd);
        }

        if(rptr == NULL)
        {
            if(debug) fprintf(stdout,"Unable to connect to server %s:%d\n", hostname, hostport);
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
        if(debug) fprintf(stderr,"No hosts found. Exiting...\n");
    }

    if(debug) fprintf(stdout, "create_connection: result=%d\n", result);

    return result;
}
