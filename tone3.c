#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <stdint.h>

int main(int argc, char *argv[]) {
    int freq, dur, fd_val, fd_dir;
    uint32_t half_us, total, i;

    if (argc < 2) { printf("Usage: tone <freq> [ms]\n"); return 1; }
    freq = atoi(argv[1]);
    dur = argc > 2 ? atoi(argv[2]) : 1000;

    fd_dir = open("/sys/class/gpio/gpio117/direction", O_WRONLY);
    if (fd_dir < 0) { perror("direction"); return 1; }
    write(fd_dir, "out", 3);
    close(fd_dir);

    fd_val = open("/sys/class/gpio/gpio117/value", O_WRONLY);
    if (fd_val < 0) { perror("value"); return 1; }

    if (freq == 0) {
        write(fd_val, "0", 1);
        printf("OFF\n");
    } else {
        half_us = 500000 / freq;
        total = (uint32_t)dur * 1000 / (half_us * 2);
        printf("Tone %dHz %dms (%d cycles)\n", freq, dur, total);

        for (i = 0; i < total; i++) {
            lseek(fd_val, 0, SEEK_SET);
            write(fd_val, "1", 1);
            usleep(half_us);
            lseek(fd_val, 0, SEEK_SET);
            write(fd_val, "0", 1);
            usleep(half_us);
        }
    }

    close(fd_val);
    return 0;
}
