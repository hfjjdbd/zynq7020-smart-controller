# AXI Buzzer PWM

This directory contains the FPGA-side PWM block for the `FPGA` branch. The
target is a MYIR Z-turn XC7Z020 board, but the exact PCB revision is not
confirmed.

If you are new to Vivado, start with `docs/vivado-beginner-fpga-pwm.md`.

The current working board runs Xillinux/Ubuntu 12.04 and exposes the buzzer as
Linux GPIO 117. The live device tree shows the old `gpio-beep` node using GPIO
`0x75` (117), which is the PS GPIO EMIO path.

Do not start by driving the buzzer. First build and boot the no-pin
`axi_selftest` design from `vivado/rtl/axi_selftest.v`. Only after that passes
should PWM be tested. Treat `BP/P18/LVCMOS33` as a candidate buzzer constraint
until the physical board revision is confirmed or the risk is explicitly
accepted.

## Register Map

Default software base address: `0x43c20000`

| Offset | Name | Bits | Description |
| ---: | --- | --- | --- |
| `0x00` | CONTROL | bit 0 | `1` enables PWM output, `0` forces output low |
| `0x04` | PERIOD | 31:0 | PWM period in PL clock cycles |
| `0x08` | DUTY | 31:0 | High time in PL clock cycles |
| `0x0c` | ID | 31:0 | Read-only `0x425a5057` |

For a 100 MHz PL clock:

```text
period = 100000000 / frequency_hz
duty   = period / 2
```

Example for 440 Hz:

```text
period = 227273
duty   = 113636
```

## Vivado Integration

1. Add `rtl/axi_buzzer_pwm.v` to the Vivado project.
2. Package it as an AXI4-Lite peripheral, or instantiate it directly in the
   block design with AXI4-Lite slave ports.
3. Connect `S_AXI` to Zynq PS `M_AXI_GP0` through an AXI interconnect.
4. Assign the IP base address to `0x43c20000`, or update
   `TONE3_PWM_BASE` when running `tone3`.
5. For the self-test stage, do not connect `pwm_out` or any external pin.
6. For the later PWM stage, drive the board buzzer from `pwm_out` only after
   board identity and the candidate `BP/P18` constraint are accepted.
7. Generate a new bitstream under a new filename. Do not overwrite the known
   working `/media/boot/7z020.bit` until the new design has been tested.

## Linux Software Path

The updated `tone3` keeps the old sysfs GPIO backend as the default. Enable this
AXI PWM backend only when the matching bitstream is loaded:

```sh
TONE3_BACKEND=axi TONE3_PWM_BASE=0x43c20000 TONE3_PWM_CLK_HZ=100000000 ./tone3 440 150
```

The web API does not change. Once the AXI backend is proven, the init script can
export `TONE3_BACKEND=axi` before launching `web_server.py`.

## Device Tree Notes

When the self-test or PWM bitstream removes the old display IP, disable
`logiclk@43c00000`, `logicvc@43c10000`, and the old `gpio-beep` node in the
matching test DTB. Otherwise the Linux framebuffer/gpio-beeper drivers may keep
accessing PL logic that no longer exists.

For a quick `/dev/mem` bring-up path, a dedicated kernel driver is not required.
For a cleaner later version, add a device tree node for this IP and use UIO or a
small platform driver instead of raw `/dev/mem`.

## No-JTAG Deployment Notes

The board has `/dev/xdevcfg`, but the running Linux framebuffer driver is bound
to old PL display IP. Do not online-replace the whole PL with:

```sh
cat new.bit > /dev/xdevcfg
```

Test new bitstreams with a new filename and keep the original boot files
available for rollback. The safe order is:

1. Build `7z020-axi-selftest.bit` without external pins or display IP.
2. Build a matching `devicetree-axi-selftest.dtb` that disables old PL display
   nodes and `gpio-beep`.
3. Boot through a U-Boot test path using new filenames.
4. Verify `linux/axi_selftest.c`: scratch readback, ID `0x50574d31`, and a
   changing counter.
5. Only after that, generate and test the PWM bitstream.
