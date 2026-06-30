#define _POSIX_C_SOURCE 200809L
#define _XOPEN_SOURCE 500

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define GPIO_NUM "117"
#define GPIO_VALUE "/sys/class/gpio/gpio" GPIO_NUM "/value"
#define GPIO_DIRECTION "/sys/class/gpio/gpio" GPIO_NUM "/direction"
#define GPIO_EXPORT "/sys/class/gpio/export"
#define BEEPER_UNBIND "/sys/bus/platform/drivers/gpio-beeper/unbind"
#define BEEPER_DEVICE "gpio-beep.3"

static int write_file(const char *path, const char *text) {
    int fd = open(path, O_WRONLY);
    if (fd < 0) return -1;
    ssize_t n = write(fd, text, strlen(text));
    close(fd);
    return (n == (ssize_t)strlen(text)) ? 0 : -1;
}

static int gpio_write(int value) {
    int fd = open(GPIO_VALUE, O_WRONLY);
    if (fd < 0) return -1;
    lseek(fd, 0, SEEK_SET);
    char ch = value ? '1' : '0';
    ssize_t n = write(fd, &ch, 1);
    close(fd);
    return (n == 1) ? 0 : -1;
}

static long time_diff_ms(struct timespec start, struct timespec end) {
    return (end.tv_sec - start.tv_sec) * 1000 + (end.tv_nsec - start.tv_nsec) / 1000000;
}

static void setup_gpio(void) {
    /* Unbind beeper driver */
    int fd = open(BEEPER_UNBIND, O_WRONLY);
    if (fd >= 0) {
        write(fd, BEEPER_DEVICE, strlen(BEEPER_DEVICE));
        close(fd);
        usleep(100000);
    }

    /* Export GPIO */
    int fd2 = open(GPIO_EXPORT, O_WRONLY);
    if (fd2 >= 0) {
        write(fd2, GPIO_NUM, strlen(GPIO_NUM));
        close(fd2);
        usleep(100000);
    }

    write_file(GPIO_DIRECTION, "out");
    gpio_write(0);
}

int main(int argc, char **argv) {
    printf("=== Buzzer Hardware Test ===\n\n");

    setup_gpio();

    /* Test 1: Active buzzer check */
    printf("--- Test 1: Active Buzzer Check ---\n");
    printf("Writing GPIO HIGH for 3 seconds...\n");
    printf("LISTEN: Do you hear a single fixed-pitch beep?\n");
    printf("  YES = Active buzzer (only needs HIGH/LOW)\n");
    printf("  NO  = Passive buzzer (needs square wave)\n\n");

    gpio_write(1);
    sleep(3);
    gpio_write(0);
    printf("Done. (GPIO set LOW)\n\n");

    printf("Press Enter to continue to Test 2...\n");
    getchar();

    /* Test 2: Frequency test with sysfs */
    printf("--- Test 2: Frequency Test (sysfs) ---\n");
    printf("Playing 3 frequencies. LISTEN for pitch differences.\n\n");

    int freqs[] = {262, 349, 440, 523, 659};
    const char *names[] = {"C4", "F4", "A4", "C5", "E5"};
    int n_freqs = 5;

    for (int i = 0; i < n_freqs; i++) {
        int freq = freqs[i];
        int half_us = 500000 / freq;
        int duration_ms = 500;
        int total_writes = (duration_ms * 1000) / (half_us * 2);

        printf("  %s (%d Hz) for %d ms...\n", names[i], freq, duration_ms);

        struct timespec t_start, t_end;
        clock_gettime(CLOCK_MONOTONIC, &t_start);

        int level = 0;
        for (int j = 0; j < total_writes; j++) {
            level = !level;
            gpio_write(level);
            usleep(half_us);
        }

        clock_gettime(CLOCK_MONOTONIC, &t_end);
        long elapsed = time_diff_ms(t_start, t_end);
        printf("    elapsed: %ld ms (expected %d ms)\n", elapsed, duration_ms);
        gpio_write(0);
        usleep(200000);
    }

    printf("\nCan you hear different pitches? YES/NO\n");
    printf("Press Enter to continue to Test 3...\n");
    getchar();

    /* Test 3: GPIO write speed benchmark */
    printf("--- Test 3: GPIO Write Speed ---\n");
    printf("Measuring sysfs write latency...\n\n");

    int iterations = 1000;
    struct timespec t_start, t_end;

    clock_gettime(CLOCK_MONOTONIC, &t_start);
    for (int i = 0; i < iterations; i++) {
        gpio_write(i & 1);
    }
    clock_gettime(CLOCK_MONOTONIC, &t_end);

    long elapsed_us = (t_end.tv_sec - t_start.tv_sec) * 1000000
                    + (t_end.tv_nsec - t_start.tv_nsec) / 1000;
    double avg_us = (double)elapsed_us / iterations;

    printf("  %d GPIO writes in %ld us\n", iterations, elapsed_us);
    printf("  Average: %.1f us per write\n", avg_us);
    printf("  Max reliable freq: %.0f Hz (half-period)\n", 1000000.0 / (avg_us * 2));
    printf("  Max reliable freq: %.0f Hz (full period)\n", 1000000.0 / avg_us);

    gpio_write(0);
    printf("\n=== Test Complete ===\n");

    return 0;
}
