#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>

#define DEFAULT_BASE 0x43c20000UL
#define MAP_SIZE 4096UL
#define REG_SCRATCH 0x00
#define REG_ID 0x04
#define REG_COUNTER 0x08
#define SELFTEST_ID 0x50574d31U

static uint32_t read_reg(volatile uint8_t *regs, unsigned offset)
{
    return *(volatile uint32_t *)(regs + offset);
}

static void write_reg(volatile uint8_t *regs, unsigned offset, uint32_t value)
{
    *(volatile uint32_t *)(regs + offset) = value;
}

int main(int argc, char **argv)
{
    unsigned long base = DEFAULT_BASE;
    long page_size;
    unsigned long page_base;
    unsigned long page_offset;
    int fd;
    void *map;
    volatile uint8_t *regs;
    uint32_t before;
    uint32_t after;
    uint32_t scratch;
    uint32_t id;

    if (argc > 1) {
        base = strtoul(argv[1], NULL, 0);
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
    write_reg(regs, REG_SCRATCH, 0xa5a55a5aU);
    scratch = read_reg(regs, REG_SCRATCH);
    id = read_reg(regs, REG_ID);
    before = read_reg(regs, REG_COUNTER);
    usleep(10000);
    after = read_reg(regs, REG_COUNTER);

    printf("base=0x%08lx\n", base);
    printf("scratch=0x%08x\n", scratch);
    printf("id=0x%08x\n", id);
    printf("counter_before=0x%08x\n", before);
    printf("counter_after=0x%08x\n", after);

    munmap(map, MAP_SIZE);
    close(fd);

    if (scratch != 0xa5a55a5aU || id != SELFTEST_ID || before == after) {
        fprintf(stderr, "AXI self-test failed\n");
        return 2;
    }

    printf("AXI self-test passed\n");
    return 0;
}
