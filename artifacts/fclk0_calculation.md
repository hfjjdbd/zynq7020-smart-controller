# FCLK0 Calculation

FCLK0 is not confirmed yet.

Use this only after read-only SLCR values are captured:

```text
IO_PLL / ARM_PLL / DDR_PLL source -> FPGA0_CLK_CTRL divisor0/divisor1 -> FCLK0
```

For software, keep the clock configurable:

```text
TONE3_PWM_CLK_HZ=100000000
```

Do not bake `100 MHz` into the safety argument. It is only the default
assumption for initial arithmetic until the board clock registers are measured.
