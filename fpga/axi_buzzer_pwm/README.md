# AXI Buzzer PWM

This directory contains the first FPGA-side step for the `FPGA` branch: a
small AXI4-Lite controlled PWM block for the Z-turn Board V2 buzzer.

If you are new to Vivado, start with `docs/vivado-beginner-fpga-pwm.md`.

The current working board runs Xillinux/Ubuntu 12.04 and exposes the buzzer as
Linux GPIO 117. The live device tree shows the old `gpio-beep` node using GPIO
`0x75` (117), which is the PS GPIO EMIO path. Do not guess a package pin for the
buzzer. In Vivado, connect `pwm_out` to the same PL signal path that previously
fed EMIO[63]/GPIO117 for the buzzer.

## Register Map

Default software base address: `0x43c20000`

| Offset | Name | Bits | Description |
| ---: | --- | --- | --- |
| `0x00` | CONTROL | bit 0 | `1` enables PWM output, `0` forces output low |
| `0x04` | PERIOD | 31:0 | PWM period in PL clock cycles |
| `0x08` | DUTY | 31:0 | High time in PL clock cycles |

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
5. Drive the board buzzer from `pwm_out` using the existing buzzer PL route.
6. Generate a new bitstream under a new filename. Do not overwrite the known
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

When the PWM bitstream owns the buzzer output, disable or remove the old
`gpio-beep` node. Otherwise the Linux gpio-beeper driver may still bind to the
old GPIO path and fight the PWM design.

For a quick `/dev/mem` bring-up path, a dedicated kernel driver is not required.
For a cleaner later version, add a device tree node for this IP and use UIO or a
small platform driver instead of raw `/dev/mem`.

## No-JTAG Deployment Notes

The board has `/dev/xdevcfg`, and the SD boot partition is mounted at
`/media/boot`. Test new bitstreams with a new filename and keep the original
boot files available for rollback. The safe order is:

1. Copy the new bitstream to the boot partition with a unique name.
2. Test loading through `/dev/xdevcfg` or a temporary U-Boot setting.
3. Verify a short tone with `TONE3_BACKEND=axi`.
4. Only then update persistent boot configuration.
