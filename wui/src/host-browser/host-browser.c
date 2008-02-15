/* 
 *  Copyright (C) 2008  Red Hat, Inc.
 *  Written by Chris Lalancette <clalance@redhat.com>
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 */

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#include <time.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <string.h>
#include <errno.h>
#include <signal.h>
#include <unistd.h>

#include <avahi-client/client.h>
#include <avahi-client/lookup.h>

#include <avahi-common/simple-watch.h>
#include <avahi-common/malloc.h>
#include <avahi-common/error.h>

#ifndef DBWRITER_PATH
#define DBWRITER_PATH "./dbwriter.rb"
#endif

static AvahiSimplePoll *simple_poll = NULL;

static void usage(void)
{
  fprintf(stderr, "Usage: host-browser [OPTIONS]\n");
  fprintf(stderr, "OPTIONS:\n\n");
  fprintf(stderr, " -d\t\tRun in daemon mode (the default)\n");
  fprintf(stderr, " -h\t\tPrint this help message\n");
  fprintf(stderr, " -n\t\tRun in interactive (non-daemon) mode (useful for debugging)\n");
  exit(1);
}

static void sig_chld(int signo)
{
  int status;

  if (waitpid(-1, &status, WNOHANG) < 0) {
    fprintf(stderr, "Error doing waitpid for child\n");
    return;
  }
}

// the function to make a daemon out of this program
static int daemonize(void)
{
  pid_t pid;

  if((pid=fork()) < 0){
    return -1;
  }
  else if (pid != 0){
    exit(0);
  }

  setsid();

  //  umask(0);

  return 0;
}

static void resolve_callback(AvahiServiceResolver *r, AvahiIfIndex interface,
			     AVAHI_GCC_UNUSED AvahiProtocol protocol,
			     AvahiResolverEvent event, const char *name,
			     const char *type, const char *domain,
			     const char *host_name, const AvahiAddress *address,
			     uint16_t port, AvahiStringList *txt,
			     AvahiLookupResultFlags flags,
			     AVAHI_GCC_UNUSED void* userdata)
{
    assert(r);

    /* Called whenever a service has been resolved successfully or timed out */

    switch (event) {
        case AVAHI_RESOLVER_FAILURE:
            break;

        case AVAHI_RESOLVER_FOUND: {
	  char a[AVAHI_ADDRESS_STR_MAX];
	  in_addr_t remote;
	  struct hostent *host;
	  char *argv[3];
	  pid_t pid;
	  int ret;
	  char *libvirt_hostname;

	  avahi_address_snprint(a, sizeof(a), address);

	  remote = inet_addr(a);
	  host = gethostbyaddr(&remote, sizeof(remote), AF_INET);
	  if (host == NULL) {
	    // we failed to resolve the address to a hostname; we'll just try
	    // with the IP address
	    libvirt_hostname = a;
	  }
	  else {
	    libvirt_hostname = host->h_name;
	  }

	  argv[0] = DBWRITER_PATH;
	  argv[1] = libvirt_hostname;
	  argv[2] = NULL;

	  pid = fork();

	  if (pid < 0) {
	    fprintf(stderr, "Failed to fork: %s\n",strerror(errno));
	  }
	  else if (pid == 0) {
	    // child
	    ret = execv(DBWRITER_PATH, argv);
	    if (ret < 0) {
	      fprintf(stderr, "Failed to exec %s: %s\n",DBWRITER_PATH,strerror(errno));
	    }
	  }
	  else {
	    // parent, do nothing; we'll catch the child exits with SIGCHLD
	  }

	  break;
        }
    }

    avahi_service_resolver_free(r);
}

static void browse_callback(AvahiServiceBrowser *b, AvahiIfIndex interface,
			    AvahiProtocol protocol, AvahiBrowserEvent event,
			    const char *name, const char *type,
			    const char *domain,
			    AVAHI_GCC_UNUSED AvahiLookupResultFlags flags,
			    void* userdata)
{    
    AvahiClient *c = userdata;
    assert(b);

    /* Called whenever a new services becomes available on the LAN or is removed from the LAN */

    switch (event) {
        case AVAHI_BROWSER_FAILURE:
            
            avahi_simple_poll_quit(simple_poll);
            return;

        case AVAHI_BROWSER_NEW:
            /* We ignore the returned resolver object. In the callback
               function we free it. If the server is terminated before
               the callback function is called the server will free
               the resolver for us. */

            if (!(avahi_service_resolver_new(c, interface, protocol, name, type, domain, AVAHI_PROTO_UNSPEC, 0, resolve_callback, c)))
                fprintf(stderr, "Failed to resolve service '%s': %s\n", name, avahi_strerror(avahi_client_errno(c)));
            
            break;

        case AVAHI_BROWSER_REMOVE:
            break;

        case AVAHI_BROWSER_ALL_FOR_NOW:
        case AVAHI_BROWSER_CACHE_EXHAUSTED:
            break;
    }
}

static void client_callback(AvahiClient *c, AvahiClientState state,
			    AVAHI_GCC_UNUSED void * userdata)
{
    assert(c);

    /* Called whenever the client or server state changes */

    if (state == AVAHI_CLIENT_FAILURE) {
        fprintf(stderr, "Server connection failure: %s\n", avahi_strerror(avahi_client_errno(c)));
        avahi_simple_poll_quit(simple_poll);
    }
}

int main(AVAHI_GCC_UNUSED int argc, AVAHI_GCC_UNUSED char *argv[])
{
    AvahiClient *client = NULL;
    AvahiServiceBrowser *sb = NULL;
    int error;
    int ret = 1;
    int daemon_mode = 1;
    int c;
    struct sigaction act;

    while ((c = getopt(argc, argv,":dhn")) != -1) {
      switch(c) {
      case 'd':
	daemon_mode = 1;
	break;
      case 'h':
	usage();
	break;
      case 'n':
	daemon_mode = 0;
	break;
      default:
	usage();
	break;
      }
    }

    if ((argc - optind) != 0) {
      usage();
    }

    if (daemon_mode) {
        daemonize();
    }

    act.sa_handler = sig_chld;
    sigemptyset(&act.sa_mask);
    act.sa_flags = SA_NOCLDSTOP;
    sigaction(SIGCHLD, &act, NULL);

    /* Allocate main loop object */
    if (!(simple_poll = avahi_simple_poll_new())) {
        fprintf(stderr, "Failed to create simple poll object.\n");
        goto fail;
    }

    /* Allocate a new client */
    client = avahi_client_new(avahi_simple_poll_get(simple_poll), 0, client_callback, NULL, &error);

    /* Check wether creating the client object succeeded */
    if (!client) {
        fprintf(stderr, "Failed to create client: %s\n", avahi_strerror(error));
        goto fail;
    }
    
    /* Create the service browser */
    if (!(sb = avahi_service_browser_new(client, AVAHI_IF_UNSPEC, AVAHI_PROTO_UNSPEC, "_libvirt._tcp", NULL, 0, browse_callback, client))) {
        fprintf(stderr, "Failed to create service browser: %s\n", avahi_strerror(avahi_client_errno(client)));
        goto fail;
    }

    /* Run the main loop */
    avahi_simple_poll_loop(simple_poll);
    
    ret = 0;
    
fail:
    
    /* Cleanup things */
    if (sb)
        avahi_service_browser_free(sb);
    
    if (client)
        avahi_client_free(client);

    if (simple_poll)
        avahi_simple_poll_free(simple_poll);

    return ret;
}
