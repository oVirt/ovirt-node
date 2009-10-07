sbin_PROGRAMS = gptsync showpart

EXTRA_DIST = README.gptsync

gptsync_SOURCES = \
  gptsync.h \
  syslinux_mbr.h \
  gptsync.c \
  lib.c \
  os_unix.c

showpart_SOURCES = \
  gptsync.h \
  showpart.c \
  lib.c \
  os_unix.c

gptsync_CPPFLAGS = $(AM_CPPFLAGS) -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -DPROGNAME=gptsync
showpart_CPPFLAGS = $(AM_CPPFLAGS) -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -DPROGNAME=showpart

