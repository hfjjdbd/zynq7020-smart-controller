# Vivado Beginner Path For FPGA Buzzer PWM

This guide is for the current ZYNQ7020 Smart Controller project. It assumes no
Vivado background.

The blog article in `参考资料/` is useful for understanding the basic idea:
a passive buzzer sounds when FPGA logic outputs a square wave. Do not copy that
design directly. That article hard-codes a song in Verilog and drives display
tubes. This project should keep song parsing and Web control in Linux, and use
FPGA only as a stable PWM generator.

## What You Are Building

Keep this mental model:

```text
Web page
  -> Python server
  -> tone3
  -> AXI-Lite registers
  -> AXI self-test first
  -> FPGA PWM later
  -> buzzer only after board identity/risk is accepted
```

The self-test block comes first and has these registers:

```text
0x00 SCRATCH read/write
0x04 ID      read-only 0x50574D31
0x08 COUNTER continuously changing
```

The later PWM block has these software-visible registers:

```text
0x00 CONTROL  bit0 enable
0x04 PERIOD   clock cycles per waveform period
0x08 DUTY     high-level clock cycles
0x0C ID       read-only 0x425A5057
```

For a 100 MHz FPGA clock and 440 Hz tone:

```text
PERIOD = 100000000 / 440 = 227273
DUTY   = PERIOD / 2      = 113636
```

## Important Difference From The Blog

The blog design:

```text
FPGA stores the whole song
FPGA decides the next note
FPGA drives buzzer directly
FPGA drives display tubes
```

This project:

```text
Linux stores song.txt
Linux decides the next note
FPGA only outputs the requested frequency
Web API stays unchanged
```

That is much easier to debug on Zynq.

## Vivado Steps

### 1. Create Or Open A Zynq Project

Use the exact part for the board:

```text
xc7z020clg400-2
```

Do not select a MYIR V2 board preset. The exact PCB revision is not confirmed.
The current plan keeps the working `BOOT.bin`/FSBL and only generates a new PL
bitstream plus a matching test DTB.

### 2. Create A Block Design

In Vivado:

```text
Flow Navigator -> IP Integrator -> Create Block Design
```

Add:

```text
ZYNQ7 Processing System
```

Run:

```text
Run Block Automation
```

Only enable the minimum PL path needed for AXI access:

```text
M_AXI_GP0 enabled
FCLK_CLK0 enabled
FCLK_RESET0_N enabled
```

Do not generate a new FSBL or replace `BOOT.bin`.

### 3. Enable AXI GP0

Open the ZYNQ7 Processing System configuration.

Enable:

```text
PS-PL Configuration -> AXI Non Secure Enablement -> GP Master AXI Interface -> M AXI GP0
```

This lets ARM/Linux write registers inside PL.

### 4. Add The AXI Self-Test RTL First

Add this source file to Vivado:

```text
vivado/rtl/axi_selftest.v
```

Then choose one of these paths:

```text
Easy Vivado path: Package it as a custom AXI4-Lite IP
Manual path: Add Module directly and wire AXI signals yourself
```

For a beginner, use the custom IP path:

```text
Tools -> Create and Package New IP
```

Select:

```text
Create a new AXI4 peripheral
Interface type: Lite
Mode: Slave
Number of registers: 3
```

Then replace the generated user logic with `axi_selftest.v`, or instantiate
`axi_selftest` from inside the generated wrapper.

### 5. Connect AXI

In the block design:

```text
ZYNQ7 M_AXI_GP0
  -> AXI Interconnect
  -> axi_selftest S_AXI
```

Vivado can usually add the AXI interconnect automatically when you run:

```text
Run Connection Automation
```

### 6. Assign Address

Open:

```text
Address Editor
```

Set the self-test IP base address to:

```text
0x43C20000
```

If Vivado forces another address, that is okay, but then run `tone3` with the
matching value:

```sh
TONE3_PWM_BASE=0xYOUR_ADDRESS
```

### 7. Do Not Connect The Buzzer Yet

The first bitstream must not connect to P18 or the buzzer. It should contain
only the Zynq PS, AXI interconnect, and the self-test AXI registers. It should
not include the old display IP.

The candidate later buzzer constraint is:

```tcl
set_property PACKAGE_PIN P18 [get_ports BP]
set_property IOSTANDARD LVCMOS33 [get_ports BP]
```

Treat that as unconfirmed until the board photos or manual risk acceptance
settle the hardware identity.

### 8. Generate Bitstream

Run:

```text
Generate Bitstream
```

Export a new bitstream with a safe name:

```text
7z020-axi-selftest.bit
```

Do not overwrite the known working:

```text
/media/boot/7z020.bit
```

## No-JTAG Load And Test

Do not online-replace the whole PL from running Linux. The current Linux has
`logicvc` framebuffer drivers bound to old PL display IP, so this is unsafe:

```sh
cat new.bit > /dev/xdevcfg
```

The safer no-JTAG flow is:

```text
old BOOT.bin
  -> U-Boot
  -> load 7z020-axi-selftest.bit
  -> load devicetree-axi-selftest.dtb
  -> boot Linux
```

The test DTB must disable:

```text
logiclk@43c00000
logicvc@43c10000
gpio-beep
```

Any copy to `/media/boot`, boot-item switch, or reboot requires explicit user
confirmation first.

After the self-test boot succeeds, compile and run `linux/axi_selftest.c` on the
board. Only after scratch readback, ID `0x50574D31`, and counter movement pass
should you generate the PWM bitstream and run a short PWM test.

## What To Ignore For Now

Do not do these in the first FPGA version:

- Do not put the whole song in Verilog.
- Do not add seven-segment display logic.
- Do not add interrupts.
- Do not add AXI DMA.
- Do not replace the Web API.
- Do not overwrite the working boot bitstream.

First target:

```text
one AXI register write -> one stable FPGA square wave -> buzzer sounds
```

After that works, the rest becomes much less scary.
