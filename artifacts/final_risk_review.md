# Final Risk Review

## Does this still depend on unverified V2 assumptions?

No. The current working assumption is:

```text
MYIR Z-turn XC7Z020, exact PCB revision unconfirmed
```

The packaging label is `MYS-7Z020-C(766) PCBA`. Do not use a V2 board preset,
V2 DDR parameters, V2 PHY assumptions, or a newly generated V2 FSBL.

## What is the evidence for P18?

P18 is only a candidate buzzer pin. It comes from cross-checking public MYIR
Z-turn pin references where `BP/P18/LVCMOS33` appears consistent, but the
actual board revision is still unconfirmed. The self-test stage does not connect
P18 or drive the buzzer.

## Does the new bitstream fully remove the old display IP?

That is the requirement for generated self-test and PWM bitstreams. The current
repository provides RTL and Vivado scaffolding only; no bitstream has been
generated in this commit.

## Does the test DTB disable old display drivers and gpio-beep?

That is required. The DTS files in `device-tree/` are templates/fragments that
document the required edits: disable `logiclk@43c00000`, `logicvc@43c10000`,
and `gpio-beep`. A real bootable DTB must be produced from the current working
board DTB before testing.

## How do we recover after failure?

Keep the original boot files untouched:

```text
/media/boot/BOOT.bin
/media/boot/7z020.bit
/media/boot/7z020-lcd.bit
/media/boot/devicetree.dtb
/media/boot/uEnv.txt
```

Test files must use new names such as `7z020-axi-selftest.bit` and
`devicetree-axi-selftest.dtb`. If a test boot fails, power cycle and boot the
original `uEnv.txt`/bitstream path.

## Is Codex stopped waiting for user confirmation?

Yes. Any copy to `/media/boot`, boot-item switch, online PL load, or reboot
requires explicit user confirmation first.
