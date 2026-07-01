#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define DEFAULT_BASE 0x43c20000UL
#define DEFAULT_CLK_HZ 100000000UL
#define MAP_SIZE 4096UL
#define REG_CONTROL 0x00
#define REG_PERIOD 0x04
#define REG_DUTY 0x08
#define REG_ID 0x0c
#define PWM_ID 0x425a5057U

static void write_reg(volatile uint8_t *regs, unsigned offset, uint32_t value)
{
    *(volatile uint32_t *)(regs + offset) = value;
}

static uint32_t read_reg(volatile uint8_t *regs, unsigned offset)
{
    return *(volatile uint32_t *)(regs + offset);
}

static void sleep_ms(unsigned ms)
{
    struct timespec req;
    req.tv_sec = ms / 1000U;
    req.tv_nsec = (long)(ms % 1000U) * 1000000L;
    while (nanosleep(&req, &req) != 0 && errno == EINTR) {
    }
}

int main(int argc, char **argv)
{
    unsigned long base = DEFAULT_BASE;
    unsigned long clk_hz = DEFAULT_CLK_HZ;
    unsigned long freq_hz = 440;
    unsigned duration_ms = 150;
    unsigned long period;
    long page_size;
    unsigned long page_base;
    unsigned long page_offset;
    int fd;
    void *map;
    volatile uint8_t *regs;
    uint32_t id;

    if (argc > 1) freq_hz = strtoul(argv[1], NULL, 0);
    if (argc > 2) duration_ms = (unsigned)strtoul(argv[2], NULL, 0);
    if (argc > 3) base = strtoul(argv[3], NULL, 0);
    if (argc > 4) clk_hz = strtoul(argv[4], NULL, 0);

    if (freq_hz == 0 || duration_ms > 1000) {
        fprintf(stderr, "usage: %s [freq_hz<= audible] [duration_ms<=1000] [base] [clk_hz]\n", argv[0]);
        return 1;
    }

    period = clk_hz / freq_hz;
    if (period == 0 || period > 0xffffffffUL) {
        fprintf(stderr, "invalid period\n");
        return 1;
    }

    page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0) {
        perror("sysconf");
        return 1;
    }

    page_base = base & ~((unsigned long)page_size - 1UL);
    page_offset = base - page_base;

    fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (fd < 0) {
        perror("open /dev/mem");
        return 1;
    }

    map = mmap(NULL, MAP_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, page_base);
    if (map == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return 1;
    }

    regs = (volatile uint8_t *)map + page_offset;
    id = read_reg(regs, REG_ID);
    if (id != PWM_ID) {
        fprintf(stderr, "unexpected PWM ID: 0x%08x\n", id);
        munmap(map, MAP_SIZE);
        close(fd);
        return 2;
    }

    write_reg(regs, REG_CONTROL, 0);
    write_reg(regs, REG_PERIOD, (uint32_t)period);
    write_reg(regs, REG_DUTY, (uint32_t)(period / 2UL));
    write_reg(regs, REG_CONTROL, 1);
    sleep_ms(duration_ms);
    write_reg(regs, REG_CONTROL, 0);

    munmap(map, MAP_SIZE);
    close(fd);
    return 0;
}
