
/* comm.c -- Contains communications routines.
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

ssize_t
saferead(int fd, char *buf, size_t count)
{
    ssize_t bytes, offset;

    int len_left;

    int done = 0;

    offset = 0;

    len_left = count;

    DEBUG("Begin saferead(%d, %p, %d)\n", fd, buf, count);

    while (!done) {
        DEBUG("Before read(%d,%p,%d)\n", fd, buf + offset, len_left);

        bytes = read(fd, buf + offset, len_left);

        DEBUG("After read: bytes=%d\n", bytes);

        if (bytes == 0) {
            done = 1;
        } else if (bytes > 0) {
            offset += bytes;
            len_left -= bytes;
            done = 1;
        } else if (errno == EINTR) {
            continue;
        } else {
            done = 1;
        }

        DEBUG("End of decision loop: offset=%d, len_left=%dl, done=%d\n",
              offset, len_left, done);
    }

    return offset;
}

ssize_t
safewrite(int fd, const void *buf, size_t count)
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
        buf = (const char *) buf + r;
        count -= r;
        nwritten += r;
    }
    return nwritten;
}
