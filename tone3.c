#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define GPIO_NUM "117"
#define GPIO_BASE "/sys/class/gpio/gpio" GPIO_NUM
#define GPIO_VALUE GPIO_BASE "/value"
#define GPIO_DIRECTION GPIO_BASE "/direction"
#define GPIO_EXPORT "/sys/class/gpio/export"
#define BEEPER_UNBIND "/sys/bus/platform/drivers/gpio-beeper/unbind"
#define BEEPER_DEVICE "gpio-beep.3"

#define MAX_FREQ_HZ 5000
#define MAX_DURATION_MS 60000
#define GPIO_WAIT_RETRIES 100
#define GPIO_WAIT_NS 10000000L

static volatile sig_atomic_t g_stop_requested = 0;
static int g_value_fd = -1;

static void on_signal(int signo) {
    (void)signo;
    g_stop_requested = 1;
}

static int write_text_file(const char *path, const char *text) {
    int fd = open(path, O_WRONLY);
    if (fd < 0) {
        return -1;
    }

    size_t len = strlen(text);
    ssize_t written = write(fd, text, len);
    int saved_errno = errno;

    if (close(fd) < 0 && written == (ssize_t)len) {
        return -1;
    }

    errno = saved_errno;
    return written == (ssize_t)len ? 0 : -1;
}

static int gpio_write_value(int value) {
    if (g_value_fd < 0) {
        errno = EBADF;
        return -1;
    }

    if (lseek(g_value_fd, 0, SEEK_SET) < 0) {
        return -1;
    }

    const char ch = value ? '1' : '0';
    return write(g_value_fd, &ch, 1) == 1 ? 0 : -1;
}

static void gpio_silence(void) {
    if (g_value_fd >= 0) {
        (void)gpio_write_value(0);
    }
}

static int wait_for_path(const char *path) {
    struct timespec delay = {
        .tv_sec = 0,
        .tv_nsec = GPIO_WAIT_NS,
    };

    for (int i = 0; i < GPIO_WAIT_RETRIES; ++i) {
        if (access(path, F_OK) == 0) {
            return 0;
        }
        nanosleep(&delay, NULL);
    }

    errno = ENOENT;
    return -1;
}

static int setup_gpio(void) {
    if (access(BEEPER_UNBIND, W_OK) == 0) {
        if (write_text_file(BEEPER_UNBIND, BEEPER_DEVICE) < 0) {
            if (errno != ENODEV && errno != EINVAL && errno != ENOENT) {
                perror("warning: unbind gpio-beeper");
            }
        }
    }

    if (access(GPIO_BASE, F_OK) != 0) {
        if (write_text_file(GPIO_EXPORT, GPIO_NUM) < 0) {
            if (errno != EBUSY) {
                perror("export gpio117");
                return -1;
            }
        }
    }

    if (wait_for_path(GPIO_DIRECTION) < 0) {
        perror("wait gpio117 direction");
        return -1;
    }

    if (write_text_file(GPIO_DIRECTION, "out") < 0) {
        perror("set gpio117 direction");
        return -1;
    }

    if (wait_for_path(GPIO_VALUE) < 0) {
        perror("wait gpio117 value");
        return -1;
    }

    g_value_fd = open(GPIO_VALUE, O_WRONLY);
    if (g_value_fd < 0) {
        perror("open gpio117 value");
        return -1;
    }

    if (gpio_write_value(0) < 0) {
        perror("initialize gpio117 value");
        close(g_value_fd);
        g_value_fd = -1;
        return -1;
    }

    return 0;
}

static struct timespec timespec_add_ns(
    struct timespec value,
    int64_t nanoseconds
) {
    value.tv_sec += nanoseconds / 1000000000LL;
    value.tv_nsec += nanoseconds % 1000000000LL;

    if (value.tv_nsec >= 1000000000L) {
        value.tv_sec += 1;
        value.tv_nsec -= 1000000000L;
    }

    return value;
}

static int sleep_until(const struct timespec *deadline) {
    int rc;

    do {
        rc = clock_nanosleep(
            CLOCK_MONOTONIC,
            TIMER_ABSTIME,
            deadline,
            NULL
        );
    } while (rc == EINTR && !g_stop_requested);

    if (rc != 0 && rc != EINTR) {
        errno = rc;
        return -1;
    }

    return 0;
}

static int sleep_ms(int duration_ms) {
    struct timespec now;

    if (clock_gettime(CLOCK_MONOTONIC, &now) < 0) {
        return -1;
    }

    struct timespec deadline =
        timespec_add_ns(now, (int64_t)duration_ms * 1000000LL);

    return sleep_until(&deadline);
}

static int play_tone(int freq, int duration_ms) {
    if (freq < 0 || freq > MAX_FREQ_HZ) {
        fprintf(stderr, "invalid frequency: %d\n", freq);
        errno = EINVAL;
        return -1;
    }

    if (duration_ms < 1 || duration_ms > MAX_DURATION_MS) {
        fprintf(stderr, "invalid duration: %d ms\n", duration_ms);
        errno = EINVAL;
        return -1;
    }

    if (freq == 0) {
        gpio_silence();
        return sleep_ms(duration_ms);
    }

    const int64_t half_period_ns =
        1000000000LL / ((int64_t)freq * 2LL);

    struct timespec deadline;
    if (clock_gettime(CLOCK_MONOTONIC, &deadline) < 0) {
        return -1;
    }

    const int64_t duration_ns =
        (int64_t)duration_ms * 1000000LL;

    int64_t elapsed_ns = 0;
    int level = 0;

    while (!g_stop_requested && elapsed_ns < duration_ns) {
        level = !level;

        if (gpio_write_value(level) < 0) {
            perror("write gpio value");
            gpio_silence();
            return -1;
        }

        deadline = timespec_add_ns(deadline, half_period_ns);

        if (sleep_until(&deadline) < 0) {
            perror("clock_nanosleep");
            gpio_silence();
            return -1;
        }

        elapsed_ns += half_period_ns;
    }

    gpio_silence();
    return 0;
}

static int parse_positive_int(
    const char *text,
    int min_value,
    int max_value,
    int *result
) {
    char *end = NULL;
    errno = 0;

    long value = strtol(text, &end, 10);

    if (
        errno != 0 ||
        end == text ||
        *end != '\0' ||
        value < min_value ||
        value > max_value
    ) {
        return -1;
    }

    *result = (int)value;
    return 0;
}

static int play_song_file(const char *path) {
    FILE *file = fopen(path, "r");
    if (!file) {
        perror("open song file");
        return -1;
    }

    char line[256];
    unsigned long line_number = 0;
    unsigned long note_count = 0;
    int status = 0;

    while (!g_stop_requested && fgets(line, sizeof(line), file)) {
        ++line_number;

        char *cursor = line;
        while (*cursor == ' ' || *cursor == '\t') {
            ++cursor;
        }

        if (
            *cursor == '\0' ||
            *cursor == '\n' ||
            *cursor == '#'
        ) {
            continue;
        }

        int freq = 0;
        int duration_ms = 0;
        char extra = '\0';

        int fields = sscanf(
            cursor,
            "%d %d %c",
            &freq,
            &duration_ms,
            &extra
        );

        if (fields != 2) {
            fprintf(
                stderr,
                "invalid song line %lu: %s",
                line_number,
                line
            );
            status = -1;
            break;
        }

        if (
            freq < 0 ||
            freq > MAX_FREQ_HZ ||
            duration_ms < 1 ||
            duration_ms > MAX_DURATION_MS
        ) {
            fprintf(
                stderr,
                "out-of-range song line %lu: freq=%d duration=%d\n",
                line_number,
                freq,
                duration_ms
            );
            status = -1;
            break;
        }

        if (play_tone(freq, duration_ms) < 0) {
            status = -1;
            break;
        }

        ++note_count;
    }

    if (ferror(file)) {
        perror("read song file");
        status = -1;
    }

    fclose(file);
    gpio_silence();

    fprintf(
        stdout,
        "song finished: %lu events%s\n",
        note_count,
        g_stop_requested ? " (stopped)" : ""
    );

    return status;
}

static void print_usage(const char *program) {
    fprintf(
        stderr,
        "Usage:\n"
        "  %s <freq_hz> [duration_ms]\n"
        "  %s song <song_file>\n"
        "  %s stop\n",
        program,
        program,
        program
    );
}

int main(int argc, char **argv) {
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    action.sa_handler = on_signal;
    sigemptyset(&action.sa_mask);

    if (
        sigaction(SIGINT, &action, NULL) < 0 ||
        sigaction(SIGTERM, &action, NULL) < 0 ||
        sigaction(SIGHUP, &action, NULL) < 0
    ) {
        perror("sigaction");
        return EXIT_FAILURE;
    }

    if (setup_gpio() < 0) {
        return EXIT_FAILURE;
    }

    int status = EXIT_SUCCESS;

    if (argc == 2 && strcmp(argv[1], "stop") == 0) {
        gpio_silence();
    } else if (
        argc == 3 &&
        strcmp(argv[1], "song") == 0
    ) {
        if (play_song_file(argv[2]) < 0) {
            status = EXIT_FAILURE;
        }
    } else if (argc == 2 || argc == 3) {
        int freq = 0;
        int duration_ms = 1000;

        if (
            parse_positive_int(
                argv[1],
                0,
                MAX_FREQ_HZ,
                &freq
            ) < 0
        ) {
            fprintf(stderr, "invalid frequency: %s\n", argv[1]);
            print_usage(argv[0]);
            status = EXIT_FAILURE;
            goto cleanup;
        }

        if (
            argc == 3 &&
            parse_positive_int(
                argv[2],
                1,
                MAX_DURATION_MS,
                &duration_ms
            ) < 0
        ) {
            fprintf(stderr, "invalid duration: %s\n", argv[2]);
            print_usage(argv[0]);
            status = EXIT_FAILURE;
            goto cleanup;
        }

        if (play_tone(freq, duration_ms) < 0) {
            status = EXIT_FAILURE;
        }
    } else {
        print_usage(argv[0]);
        status = EXIT_FAILURE;
    }

cleanup:
    gpio_silence();

    if (g_value_fd >= 0) {
        close(g_value_fd);
        g_value_fd = -1;
    }

    return status;
}
