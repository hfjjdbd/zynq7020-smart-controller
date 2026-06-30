#define _POSIX_C_SOURCE 200809L
#define _XOPEN_SOURCE 500

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define GPIO_BASE "/sys/class/gpio/gpio117"
#define GPIO_VALUE GPIO_BASE "/value"
#define GPIO_DIRECTION GPIO_BASE "/direction"
#define GPIO_EXPORT "/sys/class/gpio/export"
#define BEEPER_UNBIND "/sys/bus/platform/drivers/gpio-beeper/unbind"
#define BEEPER_DEVICE "gpio-beep.3"

#define MAX_FREQ_HZ 2000
#define MAX_DURATION_MS 60000
#define GPIO_WAIT_RETRIES 100
#define GPIO_WAIT_NS 10000000L

/* Standard note frequencies: C1-B5, 60 notes */
/* Index 0=rest, 1=C1, 2=C#1, ..., 13=C2, ..., 60=B5 */
static const int NOTE_FREQ[61] = {
    0,                                                              /* 0: rest */
    33, 35, 37, 39, 41, 44, 46, 49, 52, 55, 58, 62,              /* C1-B1 */
    65, 69, 73, 78, 82, 87, 93, 98, 104, 110, 117, 123,          /* C2-B2 */
    131, 139, 147, 156, 165, 175, 185, 196, 208, 220, 233, 247,  /* C3-B3 */
    262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466, 494,  /* C4-B4 */
    523, 554, 587, 622, 659, 698, 740, 784, 831, 880, 932, 988,  /* C5-B5 */
};

static volatile sig_atomic_t g_stop_requested = 0;
static int g_value_fd = -1;
static long g_gpio_write_ns = 50000;

static void on_signal(int signo) { (void)signo; g_stop_requested = 1; }

static int write_text_file(const char *path, const char *text) {
    int fd = open(path, O_WRONLY);
    if (fd < 0) return -1;
    size_t len = strlen(text);
    ssize_t written = write(fd, text, len);
    int saved = errno;
    close(fd);
    errno = saved;
    return written == (ssize_t)len ? 0 : -1;
}

static int gpio_write_value(int value) {
    if (g_value_fd < 0) { errno = EBADF; return -1; }
    if (lseek(g_value_fd, 0, SEEK_SET) < 0) return -1;
    const char ch = value ? '1' : '0';
    return write(g_value_fd, &ch, 1) == 1 ? 0 : -1;
}

static void gpio_silence(void) { if (g_value_fd >= 0) gpio_write_value(0); }

static int wait_for_path(const char *path) {
    struct timespec d = { .tv_sec = 0, .tv_nsec = GPIO_WAIT_NS };
    for (int i = 0; i < GPIO_WAIT_RETRIES; ++i) {
        if (access(path, F_OK) == 0) return 0;
        nanosleep(&d, NULL);
    }
    errno = ENOENT;
    return -1;
}

static int setup_gpio(void) {
    if (access(BEEPER_UNBIND, W_OK) == 0) {
        if (write_text_file(BEEPER_UNBIND, BEEPER_DEVICE) < 0) {
            if (errno != ENODEV && errno != EINVAL && errno != ENOENT)
                perror("warning: unbind gpio-beeper");
        }
    }
    if (access(GPIO_BASE, F_OK) != 0) {
        if (write_text_file(GPIO_EXPORT, "117") < 0 && errno != EBUSY) {
            perror("export gpio117"); return -1;
        }
    }
    if (wait_for_path(GPIO_DIRECTION) < 0) { perror("wait direction"); return -1; }
    if (write_text_file(GPIO_DIRECTION, "out") < 0) { perror("set direction"); return -1; }
    if (wait_for_path(GPIO_VALUE) < 0) { perror("wait value"); return -1; }
    g_value_fd = open(GPIO_VALUE, O_WRONLY);
    if (g_value_fd < 0) { perror("open value"); return -1; }
    gpio_write_value(0);
    return 0;
}

static void calibrate(void) {
    int N = 500;
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int i = 0; i < N; i++) gpio_write_value(i & 1);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    long us = (t1.tv_sec - t0.tv_sec) * 1000000L + (t1.tv_nsec - t0.tv_nsec) / 1000;
    g_gpio_write_ns = (us * 1000L) / N;
    fprintf(stderr, "GPIO write: %ld ns\n", g_gpio_write_ns);
}

static struct timespec ts_add_ns(struct timespec v, int64_t ns) {
    v.tv_sec += ns / 1000000000LL;
    v.tv_nsec += ns % 1000000000LL;
    if (v.tv_nsec >= 1000000000L) { v.tv_sec++; v.tv_nsec -= 1000000000L; }
    return v;
}

static int sleep_until(const struct timespec *dl) {
    int rc;
    do { rc = clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, dl, NULL); }
    while (rc == EINTR && !g_stop_requested);
    if (rc != 0 && rc != EINTR) { errno = rc; return -1; }
    return 0;
}

static int sleep_ms(int ms) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) < 0) return -1;
    struct timespec dl = ts_add_ns(now, (int64_t)ms * 1000000LL);
    return sleep_until(&dl);
}

static int play_tone(int freq, int duration_ms) {
    if (freq < 0 || freq > MAX_FREQ_HZ) { fprintf(stderr, "invalid freq: %d\n", freq); return -1; }
    if (duration_ms < 1 || duration_ms > MAX_DURATION_MS) { fprintf(stderr, "invalid dur: %d\n", duration_ms); return -1; }
    if (freq == 0) { gpio_silence(); return sleep_ms(duration_ms); }

    int64_t half_ns = 1000000000LL / ((int64_t)freq * 2LL);
    int64_t total_ns = (int64_t)duration_ms * 1000000LL;
    int64_t elapsed = 0;
    int level = 0;

    struct timespec deadline;
    if (clock_gettime(CLOCK_MONOTONIC, &deadline) < 0) return -1;

    while (!g_stop_requested && elapsed < total_ns) {
        level = !level;
        gpio_write_value(level);
        elapsed += half_ns;
        deadline = ts_add_ns(deadline, half_ns);
        if (half_ns > g_gpio_write_ns * 3)
            sleep_until(&deadline);
    }

    gpio_silence();
    return 0;
}

/* Map note name string to frequency using lookup table */
static int note_to_freq(const char *note) {
    static const char *names[] = {
        "C1","C#1","D1","D#1","E1","F1","F#1","G1","G#1","A1","A#1","B1",
        "C2","C#2","D2","D#2","E2","F2","F#2","G2","G#2","A2","A#2","B2",
        "C3","C#3","D3","D#3","E3","F3","F#3","G3","G#3","A3","A#3","B3",
        "C4","C#4","D4","D#4","E4","F4","F#4","G4","G#4","A4","A#4","B4",
        "C5","C#5","D5","D#5","E5","F5","F#5","G5","G#5","A5","A#5","B5",
        NULL
    };
    for (int i = 0; names[i]; i++) {
        if (!strcmp(note, names[i])) return NOTE_FREQ[i + 1];
    }
    return -1;
}

static int parse_int(const char *s, int lo, int hi, int *out) {
    char *e; errno = 0;
    long v = strtol(s, &e, 10);
    if (errno || e == s || *e || v < lo || v > hi) return -1;
    *out = (int)v; return 0;
}

static int play_song(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) { perror("open song"); return -1; }
    char line[256]; unsigned long n = 0; int st = 0;
    while (!g_stop_requested && fgets(line, sizeof(line), f)) {
        char *c = line; while (*c == ' ' || *c == '\t') c++;
        if (*c == '\0' || *c == '\n' || *c == '#') continue;
        int freq, dur;
        if (sscanf(c, "%d %d", &freq, &dur) != 2) { st = -1; break; }
        if (freq < 0 || freq > MAX_FREQ_HZ || dur < 1 || dur > MAX_DURATION_MS) { st = -1; break; }
        if (play_tone(freq, dur) < 0) { st = -1; break; }
        n++;
    }
    if (ferror(f)) st = -1;
    fclose(f); gpio_silence();
    fprintf(stdout, "song: %lu notes%s\n", n, g_stop_requested ? " (stopped)" : "");
    return st;
}

static void usage(const char *p) {
    fprintf(stderr,
        "Usage:\n"
        "  %s <freq_hz> [duration_ms]\n"
        "  %s note <note_name> [duration_ms]\n"
        "  %s song <file>\n"
        "  %s stop\n"
        "  %s scale\n"
        "\nNote names: C1-B5 (e.g. C4=262Hz, A4=440Hz)\n",
        p, p, p, p, p);
}

static void play_scale(void) {
    fprintf(stderr, "Playing C major scale C2-C5...\n");
    int notes[] = {262, 294, 330, 349, 392, 440, 494, 523};
    const char *names[] = {"C4","D4","E4","F4","G4","A4","B4","C5"};
    for (int i = 0; i < 8; i++) {
        fprintf(stderr, "  %s (%d Hz)\n", names[i], notes[i]);
        play_tone(notes[i], 500);
        if (!g_stop_requested) usleep(100000);
    }
    fprintf(stderr, "Done.\n");
}

int main(int argc, char **argv) {
    struct sigaction sa; memset(&sa, 0, sizeof(sa));
    sa.sa_handler = on_signal; sigemptyset(&sa.sa_mask);
    sigaction(SIGINT, &sa, NULL); sigaction(SIGTERM, &sa, NULL); sigaction(SIGHUP, &sa, NULL);

    if (setup_gpio() < 0) return 1;
    calibrate();

    int st = 0;
    if (argc == 2 && !strcmp(argv[1], "stop")) {
        gpio_silence();
    } else if (argc == 2 && !strcmp(argv[1], "scale")) {
        play_scale();
    } else if (argc == 3 && !strcmp(argv[1], "song")) {
        st = play_song(argv[2]);
    } else if (argc == 3 && !strcmp(argv[1], "note")) {
        int freq = note_to_freq(argv[2]);
        if (freq < 0) { fprintf(stderr, "unknown note: %s\n", argv[2]); st = 1; }
        else st = play_tone(freq, 1000);
    } else if (argc == 2 || argc == 3) {
        int freq = 0, dur = 1000;
        if (parse_int(argv[1], 0, MAX_FREQ_HZ, &freq) < 0) { usage(argv[0]); st = 1; goto end; }
        if (argc == 3 && parse_int(argv[2], 1, MAX_DURATION_MS, &dur) < 0) { usage(argv[0]); st = 1; goto end; }
        st = play_tone(freq, dur);
    } else { usage(argv[0]); st = 1; }

end:
    gpio_silence();
    if (g_value_fd >= 0) { close(g_value_fd); g_value_fd = -1; }
    return st;
}
