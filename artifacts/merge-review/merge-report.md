# Safe Selective Merge Report

## Environment

- Current project: D:\Agent\zynq7020-smart-controller
- Reviewed project: C:\Users\wby\Downloads\Gopeed\zynq7020-smart-controller-reviewed
- Git branch: codex/fpga-reviewed-merge-20260701-204846
- Backup directory: D:\Agent\zynq7020-smart-controller-backup-20260701-204846
- Operation time: 2026-07-01 20:53:37 +08:00

## Merged Files

- device-tree/devicetree-original.dts and .dtb: added from reviewed project as the real board DTB snapshot.
- device-tree/devicetree-axi-selftest.dts and .dtb: replaced fragment with full DTS/DTB derived from the real board DTB; disables old PL display and gpio-beep, adds axi-selftest@43c20000.
- device-tree/devicetree-pwm-test.dts and .dtb: replaced fragment with full DTS/DTB derived from the real board DTB; disables old PL display and gpio-beep, adds axi-buzzer-pwm@43c20000.
- device-tree/README.md: added reviewed explanation of DTB provenance and why first test uses /dev/mem rather than assuming UIO.
- docs/vivado-dtb-next-step-review.md: added reviewed next-step guide for Vivado, DTB edits, U-Boot test path, and recovery.
- boot/uEnv-axi-selftest.txt: manually merged. Kept reviewed explicit fatload/fpga loadb test path and removed mmc_loadbit_fat; kept uenvcmd as confirmation-only.
- boot/uEnv-pwm-test.txt: manually merged the same way; confirmation-only, no automatic boot.
- fpga/axi_buzzer_pwm/rtl/axi_buzzer_pwm.v: manually merged reviewed PWM safety gate requiring period >= 2, duty != 0, and duty < period.
- artifacts/sha256sums.txt: updated with reviewed DTB hashes.
- artifacts/merge-review/*: added audit reports, diffs, validation notes, and checksums.

## Not Merged

- Whole reviewed project directory: not copied over; only selected files were merged.
- README.md, AGENTS.md, linux/*.c, vivado/rtl/axi_selftest.v, docs/vivado-beginner-fpga-pwm.md: reviewed versions were identical to current or current content was retained.
- 参考资料/: left untouched and untracked.
- Any board boot files: not copied to /media/boot.

## Safety Fix Confirmation

- Full DTS merged: yes.
- logiclk@43c00000 disabled in test DTS: yes.
- logicvc@43c10000 disabled in test DTS: yes.
- gpio-beep disabled in test DTS: yes.
- AXI self-test node at 0x43c20000: yes.
- U-Boot templates avoid mmc_loadbit_fat: yes.
- U-Boot templates are confirmation-only by default: yes.
- PWM checks duty < period: yes.
- PWM reset/inactive behavior preserved: yes.
- First-stage AXI self-test still has no BP/P18/buzzer output: yes.

## Validation

- DTS/DTB: local dtc is not installed. A WSL apt installation attempt timed out and was stopped, so compile/round-trip was not rerun. Static node checks passed. Reviewed DTB files and hashes are included.
- Linux tools: compiled on the board with GCC 4.6.3 in /tmp; no execution, no /dev/mem access, no buzzer test.
- RTL lint: iverilog/verilator unavailable. A WSL apt installation attempt timed out and was stopped, so lint was not run; static review recorded.
- Forbidden command scan: only documentation warnings/prohibitions found; no script was added that writes /media/boot, runs saveenv, reboots, or loads /dev/xdevcfg.
- git diff --check: passed.

## Risks And Next Step

- Vivado has not been run.
- No bitstream has been generated.
- No file has been copied to the board boot partition.
- No U-Boot test has been executed.
- The board has not been rebooted.
- AXI self-test has not been run.
- Buzzer/PWM has not been tested.

Next manual step: open Vivado, generate only the first-stage 7z020-axi-selftest.bit, then review it together with devicetree-axi-selftest.dtb. Copying test files to /media/boot, interrupting U-Boot, rebooting, or loading FPGA must wait for explicit user confirmation.

STOPPED BEFORE BOARD MODIFICATION

REQUIRES USER CONFIRMATION BEFORE ANY /media/boot COPY, U-BOOT TEST, REBOOT, OR FPGA LOAD
