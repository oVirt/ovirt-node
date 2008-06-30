#ifndef __OVIRT_IDENTIFY_NODE_H
#define __OVIRT_IDENTIFY_NODE_H

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

#define COPY_VALUE_TO_BUFFER(value,buffer,length) \
    snprintf(buffer,length,"%s",value)

int  config(int argc,char** argv);
void usage(void);

int start_conversation(void);
int send_details(void);
int send_cpu_details(void);
int end_conversation(void);

void get_label_and_value(char* text,
                         char* label,size_t label_length,
                         char* value,size_t value_length);
t_cpu_info* create_cpu_info(void);
int get_cpu_info(void);

int send_text(char* text);
int get_text(const char *const expected);
int create_connection(void);

int debug   = 0;
int verbose = 0;
int testing = 0;

char arch[BUFFER_LENGTH];
char uuid[VIR_UUID_BUFLEN];
char memsize[BUFFER_LENGTH];
char numcpus[BUFFER_LENGTH];
char cpuspeed[BUFFER_LENGTH];
char *hostname;
int  hostport = -1;
int  socketfd;
t_cpu_info* cpu_info;

#endif
