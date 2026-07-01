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
  -> FPGA PWM
  -> buzzer
```

The FPGA block has only three software-visible registers:

```text
0x00 CONTROL  bit0 enable
0x04 PERIOD   clock cycles per waveform period
0x08 DUTY     high-level clock cycles
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
XC7Z020-2CLG400
```

If you already have an official MYIR/Z-turn Vivado project, use that first. It
is safer than creating a board design from nothing because DDR, clocks, Ethernet,
SD card, UART, and the existing PL routes are already configured.

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

This configures the basic PS side.

### 3. Enable AXI GP0

Open the ZYNQ7 Processing System configuration.

Enable:

```text
PS-PL Configuration -> AXI Non Secure Enablement -> GP Master AXI Interface -> M AXI GP0
```

This lets ARM/Linux write registers inside PL.

### 4. Add The PWM RTL

Add this source file to Vivado:

```text
fpga/axi_buzzer_pwm/rtl/axi_buzzer_pwm.v
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

Then replace the generated user logic with `axi_buzzer_pwm.v`, or instantiate
`axi_buzzer_pwm` from inside the generated wrapper.

### 5. Connect AXI

In the block design:

```text
ZYNQ7 M_AXI_GP0
  -> AXI Interconnect
  -> axi_buzzer_pwm S_AXI
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

Set the PWM IP base address to:

```text
0x43C20000
```

If Vivado forces another address, that is okay, but then run `tone3` with the
matching value:

```sh
TONE3_PWM_BASE=0xYOUR_ADDRESS
```

### 7. Connect The Buzzer Output

This is the only board-specific part.

Your running Linux device tree says the old buzzer uses GPIO 117:

```text
gpio-beep gpios = 0x75
```

On Zynq PS GPIO, GPIO 117 corresponds to:

```text
EMIO[63]
```

So do not guess a random package pin. The safest goal is:

```text
axi_buzzer_pwm pwm_out -> the old PL path that drove EMIO[63]/GPIO117 buzzer
```

If you use the official MYIR project, look for the existing buzzer or GPIO117
connection and replace that signal with `pwm_out`.

### 8. Generate Bitstream

Run:

```text
Generate Bitstream
```

Export a new bitstream with a safe name:

```text
7z020-pwm-test.bit
```

Do not overwrite the known working:

```text
/media/boot/7z020.bit
```

## No-JTAG Load And Test

Copy the bitstream:

```sh
cat 7z020-pwm-test.bit | ssh root@192.168.1.100 'cat > /media/boot/7z020-pwm-test.bit'
```

Load it temporarily:

```sh
ssh root@192.168.1.100 'cat /media/boot/7z020-pwm-test.bit > /dev/xdevcfg'
```

Test a short tone:

```sh
ssh root@192.168.1.100 'cd /root/project && TONE3_BACKEND=axi TONE3_PWM_BASE=0x43c20000 TONE3_PWM_CLK_HZ=100000000 ./tone3 440 150'
```

If it does not work, reboot the board. Because this is a temporary load, reboot
returns to the SD card boot configuration.

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
