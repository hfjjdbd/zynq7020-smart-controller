# Cross-Compile `tone3` From WSL

The Z-turn Board V2 runs a 32-bit ARM hard-float Linux userland. The existing
`/root/project/tone3` binary reports:

```text
ELF 32-bit LSB executable, ARM, EABI5
interpreter /lib/ld-linux-armhf.so.3
```

Use an `armhf` Linux cross compiler, not a bare-metal compiler.

## Install Toolchain

In WSL Ubuntu:

```sh
sudo apt update
sudo apt install -y make gcc-arm-linux-gnueabihf
```

## Build

From this repository inside WSL:

```sh
cd /mnt/d/Agent/zynq7020-smart-controller
make cross-armhf
file tone3-armhf
```

Expected output includes:

```text
ELF 32-bit LSB executable, ARM
interpreter /lib/ld-linux-armhf.so.3
```

## Deploy Safely

Keep the currently working board binary until the new one has been tested:

```sh
cat tone3-armhf | ssh root@192.168.1.100 'cat > /root/project/tone3.new'
ssh root@192.168.1.100 'chmod +x /root/project/tone3.new'
ssh root@192.168.1.100 'cd /root/project && ./tone3.new 440 150 && ./tone3.new stop'
```

After the short test passes, replace the live binary with explicit paths:

```sh
cat tone3-armhf | ssh root@192.168.1.100 'cat > /root/project/tone3'
ssh root@192.168.1.100 'chmod +x /root/project/tone3'
```

Do not overwrite `/media/boot/7z020.bit` while testing FPGA PWM. Use a new
bitstream filename and keep the old SD boot files available for rollback.
