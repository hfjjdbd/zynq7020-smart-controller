# Review: AXI self-test Vivado and DTB next steps

## 1. Repository audit

The project is still a scaffold, not a bootable FPGA deliverable:

- `vivado/create_project.tcl` creates only an empty Vivado project with RTL.
- No block design, packaged IP, generated bitstream, or Vivado reports exist.
- The previous `device-tree/*.dts` files were fragments and could not boot.
- The previous U-Boot templates called `mmc_loadbit_fat`, which is unsafe for
  this test because the board's U-Boot macro calls `get_bitstream_name` and
  resets the filename to `7z020.bit`.

This reviewed copy includes full DTB/DTS variants derived from the board's
actual DTB and corrected manual U-Boot command variables.

## 2. Clock evidence

The actual board DTB contains:

```dts
logiclk@43c00000 {
    osc-clk-freq-hz = <100000000>;
};
```

This is strong evidence that the existing PL input clock is 100 MHz. Use
100 MHz as the Vivado FCLK0 timing metadata for the first self-test, while still
keeping the Linux software clock configurable.

## 3. Vivado block design: beginner path

### 3.1 Create the project

Use Vivado with this part only:

```text
xc7z020clg400-2
```

Do not select a MYIR/V2 board preset. Do not generate an FSBL or BOOT.bin.

The existing script may be run from the repository root:

```sh
vivado -mode gui -source vivado/create_project.tcl
```

### 3.2 Create the block design

1. `Flow Navigator -> IP Integrator -> Create Block Design`
2. Name it `system`.
3. Add `ZYNQ7 Processing System`.
4. Click `Run Block Automation`.
5. Allow Vivado to make `DDR` and `FIXED_IO` external.

The DDR/FIXED_IO settings in this project are not being used to generate a new
FSBL. The board continues to boot through its original `BOOT.bin`.

### 3.3 Configure the PS/PL path

Double-click the Zynq PS:

1. Enable `M_AXI_GP0`.
2. Enable `FCLK_CLK0`.
3. Set FCLK0 design frequency to `100 MHz`.
4. Do not enable HP ports, ACP, PL interrupts, or extra AXI ports.

After closing the PS configuration, connect:

```text
FCLK_CLK0 -> M_AXI_GP0_ACLK
```

Add `Processor System Reset` and connect:

```text
FCLK_CLK0     -> slowest_sync_clk
FCLK_RESET0_N -> ext_reset_in
```

Use `peripheral_aresetn` as the active-low reset for the AXI interconnect and
the self-test peripheral.

### 3.4 Package `axi_selftest.v`

Recommended GUI route:

1. `Tools -> Create and Package New IP`.
2. Select `Create a new AXI4 peripheral`.
3. Name: `axi_selftest_ip`.
4. Create one AXI4-Lite slave named `S00_AXI`.
5. Data width: 32.
6. Choose 4 registers if the wizard does not permit 3.
7. Open the generated IP for editing.
8. Add `vivado/rtl/axi_selftest.v` to the IP project.
9. In the generated top-level wrapper, replace the generated
   `*_S00_AXI` instance with an `axi_selftest` instance.
10. Map every `S00_AXI_*` wrapper signal to the corresponding lower-case
    `s_axi_*` port.
11. Re-package the IP.

Do not place a second generated register bank in front of `axi_selftest`; the
provided RTL already implements the full AXI4-Lite slave.

### 3.5 Connect and address the IP

1. Add `axi_selftest_ip` to `system.bd`.
2. Run Connection Automation.
3. The intended path is:

```text
ZYNQ7 M_AXI_GP0 -> AXI Interconnect -> axi_selftest_ip/S00_AXI
```

4. Confirm all AXI clocks use FCLK_CLK0.
5. Confirm all active-low resets use `peripheral_aresetn`.
6. In Address Editor assign:

```text
0x43C20000
```

A 4 KiB or 64 KiB segment is acceptable. The RTL only decodes offsets
`0x00`, `0x04`, and `0x08`.

### 3.6 Validate and generate

1. `Tools -> Validate Design`.
2. Fix every error.
3. Create HDL wrapper: `Let Vivado manage wrapper`.
4. Run synthesis.
5. Run implementation.
6. Generate bitstream.
7. Copy the generated file as:

```text
7z020-axi-selftest.bit
```

The first design has no external PL pin and must not use the buzzer XDC.

## 4. Exact Linux 3.15 DTB edits

The relevant nodes in the actual DTB are direct children of `/amba`.

Add this property to each existing node:

```dts
status = "disabled";
```

Targets:

```text
/amba/logiclk@43c00000
/amba/logicvc@43c10000
/amba/gpio-beep
```

Add this node under `/amba`:

```dts
axi-selftest@43c20000 {
    compatible = "myir,axi-selftest-1.0";
    reg = <0x43c20000 0x1000>;
    status = "okay";
};
```

No interrupt property is needed. No clock property is needed for the first
driverless `/dev/mem` test.

`status = "disabled"` is valid for the old 3.15 OF platform-device path.

### Why not use `generic-uio` immediately?

`linux/axi_selftest.c` uses `/dev/mem`; it does not need a DT driver. On an old
kernel, `generic-uio` may require all of the following:

```text
CONFIG_UIO
CONFIG_UIO_PDRV_GENIRQ
uio_pdrv_genirq module or built-in driver
uio_pdrv_genirq.of_id=generic-uio in bootargs
```

Check those first. The private compatible string avoids assuming UIO support.

## 5. Correct U-Boot test path

The board's embedded U-Boot environment shows:

```text
mmc_loadbit_fat=... get_bitstream_name ... ${bitstream_image} ...
```

Therefore setting `bitstream_image=7z020-axi-selftest.bit` and then running
`mmc_loadbit_fat` does not reliably select the test file: `get_bitstream_name`
can reset it to `7z020.bit`.

The safest first test is through the USB-UART U-Boot prompt, with no `saveenv`:

```text
mmcinfo
fatload mmc 0 ${loadbit_addr} 7z020-axi-selftest.bit
fpga loadb 0 ${loadbit_addr} ${filesize}
fatload mmc 0 ${kernel_load_address} ${kernel_image}
fatload mmc 0 ${devicetree_load_address} devicetree-axi-selftest.dtb
setenv bootargs 'console=ttyPS0,115200 root=/dev/mmcblk0p2 rw earlyprintk rootfstype=ext4 rootwait devtmpfs.mount=0'
bootm ${kernel_load_address} - ${devicetree_load_address}
```

Do not run `saveenv`.

## 6. Recovery

Because the original files and environment are untouched:

1. Power off or reset the board.
2. Do not interrupt the next U-Boot countdown.
3. The normal `uEnv.txt` path calls `get_bitstream_name`.
4. U-Boot reloads the original `7z020.bit` and original `devicetree.dtb`.

A failed experimental boot therefore does not persist unless someone overwrites
the original files or saves modified U-Boot environment variables.

## 7. RTL safety fix before the PWM phase

The PWM must reject invalid duty/period combinations. Use:

```verilog
assign pwm_enable = control_reg[0] &&
                    (period_reg >= 32'd2) &&
                    (duty_reg != 32'd0) &&
                    (duty_reg < period_reg);
```

Without `duty_reg < period_reg`, an invalid register write can hold the output
continuously high. The reviewed project copy includes this correction.
