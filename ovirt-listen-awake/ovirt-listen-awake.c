/* ovirt-listen-awake: daemon to listen for and respond to AWAKE requests
 *
 * Copyright (C) 2008 Red Hat, Inc.
 * Written by Chris Lalancette <clalance@redhat.com>
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

#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <error.h>
#include <string.h>
#include <unistd.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <ctype.h>

// We only ever expect to receive the strings "AWAKE" or "IDENTIFY", so
// 20 bytes is more than enough
#define BUFLEN 20
#define LOGFILE "/var/log/ovirt-host.log"

static int streq(char *first, char *second)
{
  int first_len, second_len;

  first_len = strlen(first);
  second_len = strlen(second);

  if (first_len == second_len && strncmp(first, second, first_len) == 0)
    return 1;
  return 0;
}

// Given a buffer, find the first whitespace character, replace it with \0,
// and return
static void find_first_whitespace(char *buffer)
{
  int i;

  i = 0;
  while (buffer[i] != '\0') {
    if (isspace(buffer[i])) {
      // once we see the first whitespace character, we are done
      buffer[i] ='\0';
      break;
    }
    i++;
  }
}

static int listenSocket(int listen_port)
{
  struct sockaddr_in a;
  int s,yes;

  if (listen_port < 0) {
    error(0, 0, "Invalid listen_port %d", listen_port);
    return -1;
  }

  s = socket(AF_INET, SOCK_STREAM, 0);
  if (s < 0) {
    error(0, errno, "Failed creating socket");
    return -1;
  }

  yes = 1;
  if (setsockopt(s, SOL_SOCKET, SO_REUSEADDR,(char *)&yes, sizeof (yes)) < 0) {
    error(0, errno, "Failed setsockopt");
    close(s);
    return -1;
  }

  memset (&a, 0, sizeof (a));
  a.sin_port = htons (listen_port);
  a.sin_family = AF_INET;
  if (bind(s, (struct sockaddr *) &a, sizeof (a)) < 0) {
    error(0, errno, "Error binding to port %d", listen_port);
    close(s);
    return -1;
  }

  if (listen(s, 10) < 0) {
    error(0, errno, "Error listening on port %d", listen_port);
    close(s);
    return -1;
  }
  return s;
}

static void usage(int exitcode)
{
  printf("Usage: ovirt-listen-awake [OPTIONS]\n");
  printf("OPTIONS:\n");
  printf(" -h\t\tShow this help message\n");
  printf(" -n\t\tDo not daemonize (useful for debugging)\n");
  exit(exitcode);
}

int main(int argc, char *argv[])
{
  int listen_socket, conn;
  struct sockaddr_in client_address;
  unsigned int addrlen;
  FILE *conn_stream;
  FILE *logfile;
  char buffer[BUFLEN];
  int c;
  int do_daemon;
  int i;

  do_daemon = 1;

  while ((c=getopt(argc, argv, ":hn")) != -1) {
    switch(c) {
    case 'h':
      usage(0);
      break;
    case 'n':
      do_daemon = 0;
      break;
    default:
      usage(1);
    }
  }

  if ((argc-optind) != 0) {
    for (i = optind; i < argc ; i ++) {
      fprintf(stderr, "Extra operand %s\n", argv[i]);
    }
    error(1, 0, "Try --help for more information");
  }

  listen_socket = listenSocket(7777);
  if (listen_socket < 0)
    return 2;

  if (do_daemon) {
    logfile = fopen(LOGFILE,"a+");
    if (logfile == NULL)
      error(3, errno, "Error opening logfile %s", LOGFILE);

    // NOTE: this closes stdout and stderr
    if (daemon(0, 0) < 0)
      error(4, errno, "Error daemonizing");

    // so re-open them to the logfile here
    dup2(fileno(logfile), STDOUT_FILENO);
    dup2(fileno(logfile), STDERR_FILENO);
  }

  while (1) {
    addrlen = sizeof(client_address);
    memset(&client_address, 0, addrlen);
    memset(buffer, 0, BUFLEN);
    conn = accept(listen_socket, (struct sockaddr *)&client_address, &addrlen);
    if (conn < 0) {
      error(0, errno, "Error accepting socket");
      continue;
    }

    conn_stream = fdopen(conn, "r");
    if (conn_stream == NULL) {
      error(0, errno, "Error converting fd to stream");
      close(conn);
      continue;
    }

    if (fgets(buffer, BUFLEN, conn_stream) == NULL) {
      error(0, errno, "Error receiving data");
      fclose(conn_stream);
      continue;
    }

    find_first_whitespace(buffer);

    if (streq(buffer, "IDENTIFY")) {
      // run ovirt-identify-node against 192.168.50.2 (the WUI node)
      fprintf(stderr, "Doing identify\n");
      // FIXME: it would be best to call the "find_srv" shell script here to
      // find out where we should contact.  However, we would still have to
      // hardcode which DNS server to use (192.168.50.2), and which domain
      // name to use "priv.ovirt.org" to get this to work.  I don't have
      // a good idea how to solve this at the moment.
      system("ovirt-identify-node -s 192.168.50.2 -p 12120");
    }
    else if (streq(buffer, "AWAKE")) {
      // run ovirt-awake against 192.168.50.2
      fprintf(stderr, "Doing awake\n");
      // FIXME: I hate to duplicate this stuff here, but I can't use the
      // ovirt init scripts as-is; they depend too much on the environment
      // (in particular, which DNS server to use to resolve, and which
      // domainname).  Until I come up with a good solution for that, I'll
      // have to leave this as-is.
      system("wget -q http://192.168.50.2:80/ipa/config/krb5.ini -O /etc/krb5.conf");
      system("ovirt-awake start 192.168.50.2 12120 /etc/libvirt/krb5.tab");
    }
    else {
      error(0, 0, "Unknown command %s", buffer);
    }

    fclose(conn_stream);
  }

  close(listen_socket);
  fclose(logfile);

  return 0;
}
