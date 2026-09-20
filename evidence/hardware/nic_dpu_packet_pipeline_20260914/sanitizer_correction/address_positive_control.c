#include <stdlib.h>
int main(int argc, char **argv) {
volatile char *p=malloc(1); (void)argv; if(!p)return 2; p[argc+3]=120; free((void*)p); return 0;}
