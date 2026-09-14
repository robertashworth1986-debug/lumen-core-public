#include <limits.h>
int main(int argc, char **argv) {
volatile int value = INT_MAX; (void)argv; return value + argc; }
