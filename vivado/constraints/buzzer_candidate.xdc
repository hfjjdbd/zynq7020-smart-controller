# Candidate buzzer pin constraint.
# Do not enable this file until the physical board identity is checked or the
# risk is explicitly accepted. The current verified-safe self-test design does
# not connect this pin.

set_property PACKAGE_PIN P18 [get_ports BP]
set_property IOSTANDARD LVCMOS33 [get_ports BP]
