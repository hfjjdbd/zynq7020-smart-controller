CROSS_COMPILE ?=
TARGET ?= tone3
CFLAGS ?= -std=gnu99 -Wall -Wextra -O2
LDLIBS ?= -lrt

ifeq ($(origin CC),default)
CC := $(CROSS_COMPILE)gcc
endif

.PHONY: all cross-armhf print-toolchain

all: $(TARGET)

$(TARGET): tone3.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS) $(LDLIBS)

cross-armhf:
	$(MAKE) CROSS_COMPILE=arm-linux-gnueabihf- TARGET=tone3-armhf

print-toolchain:
	@echo CC=$(CC)
	@echo CROSS_COMPILE=$(CROSS_COMPILE)
	@echo TARGET=$(TARGET)
