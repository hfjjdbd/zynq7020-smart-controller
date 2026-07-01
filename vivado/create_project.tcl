# Vivado project scaffold for the conservative AXI self-test path.
# Run from the repository root:
#   vivado -mode batch -source vivado/create_project.tcl
#
# This script intentionally selects only the FPGA part. It does not use a MYIR
# V2 board preset and does not generate or replace FSBL/BOOT.bin.

set script_dir [file dirname [file normalize [info script]]]
set repo_dir [file normalize [file join $script_dir ..]]
set project_dir [file join $repo_dir vivado zynq7020_axi_selftest_project]

create_project zynq7020_axi_selftest $project_dir -part xc7z020clg400-2 -force
set_property target_language Verilog [current_project]

add_files -norecurse [file join $repo_dir vivado rtl axi_selftest.v]
add_files -norecurse [file join $repo_dir vivado rtl axi_buzzer_pwm.v]

puts "Project scaffold created."
puts "Next manual steps:"
puts "1. Create a block design with ZYNQ7 Processing System."
puts "2. Enable only M_AXI_GP0, FCLK_CLK0, and FCLK_RESET0_N for PL access."
puts "3. Package axi_selftest.v as an AXI4-Lite slave at 0x43C20000."
puts "4. Generate 7z020-axi-selftest.bit first. Do not connect BP/P18."
puts "5. Do not overwrite BOOT.bin, 7z020.bit, devicetree.dtb, or uEnv.txt."
