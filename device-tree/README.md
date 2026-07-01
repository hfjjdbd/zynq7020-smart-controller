# Device-tree test variants

These files are derived from the board's actual `/media/boot/devicetree.dtb`,
not from a V2 template.

- `devicetree-original.dtb/.dts`: untouched source snapshot.
- `devicetree-axi-selftest.dtb/.dts`: disables the old `logiclk`, `logicvc`,
  and `gpio-beep` nodes; adds a driverless AXI self-test node at `0x43c20000`.
- `devicetree-pwm-test.dtb/.dts`: same changes, with a PWM node.

The test node deliberately uses a private compatible string instead of
`generic-uio`. The first test program uses `/dev/mem`, which does not require
UIO support. Linux 3.15 may require `uio_pdrv_genirq.of_id=generic-uio`, a
matching kernel configuration, and a loaded module before `generic-uio` works.

To regenerate with `dtc`:

```sh
dtc -I dtb -O dts -o devicetree-original.dts devicetree-original.dtb
# Apply the documented status/node edits.
dtc -I dts -O dtb -o devicetree-axi-selftest.dtb devicetree-axi-selftest.dts
dtc -I dtb -O dts -o verify.dts devicetree-axi-selftest.dtb
```

Do not boot a test DTB unless the matching bitstream has been generated.
