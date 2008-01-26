CC=gcc
CFLAGS+=-g -Wall
OBJS=host-browser.o
LIBS=-lavahi-client

all: host-browser

host-browser: $(OBJS)
	$(CC) $(CFLAGS) -o host-browser $(OBJS) $(LIBS)

clean:
	rm -f *.o *~ host-browser
