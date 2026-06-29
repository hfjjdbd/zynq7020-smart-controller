#!/bin/bash
# WiFi 共享脚本 — 将 WiFi 网络通过有线网口共享给交换机（含DHCP）
# 用法: sudo bash share_wifi.sh [on|off|status]

WIFI_IF="wlp1s0"
ETH_IF="enp4s0"
DHCP_RANGE="192.168.1.100,192.168.1.200,255.255.255.0,12h"

check_running() {
    pgrep -x dnsmasq >/dev/null 2>&1 && echo "  dnsmasq: 运行中" || echo "  dnsmasq: 未运行"
    [ "$(cat /proc/sys/net/ipv4/ip_forward)" = "1" ] && echo "  IP转发: 已开启" || echo "  IP转发: 已关闭"
    iptables -t nat -C POSTROUTING -o "$WIFI_IF" -j MASQUERADE 2>/dev/null && echo "  NAT规则: 已配置" || echo "  NAT规则: 未配置"
}

case "${1:-on}" in
    on)
        echo "=== 开启 WiFi 共享 ==="

        if ! ip link show "$WIFI_IF" >/dev/null 2>&1; then
            echo "错误: WiFi 接口 $WIFI_IF 不存在"; exit 1
        fi
        if ! ip link show "$ETH_IF" >/dev/null 2>&1; then
            echo "错误: 有线接口 $ETH_IF 不存在"; exit 1
        fi

        if iptables -t nat -C POSTROUTING -o "$WIFI_IF" -j MASQUERADE 2>/dev/null; then
            echo "NAT 规则已存在，跳过"
        else
            echo "配置 NAT 规则..."
            iptables -I ufw-user-forward 1 -i "$ETH_IF" -o "$WIFI_IF" -j ACCEPT
            iptables -I ufw-user-forward 2 -i "$WIFI_IF" -o "$ETH_IF" -m state --state RELATED,ESTABLISHED -j ACCEPT
            iptables -t nat -A POSTROUTING -o "$WIFI_IF" -j MASQUERADE
        fi

        echo "开启 IP 转发..."
        sysctl -w net.ipv4.ip_forward=1

        if pgrep -x dnsmasq >/dev/null 2>&1; then
            echo "dnsmasq 已运行，跳过"
        else
            echo "启动 DHCP 服务..."
            dnsmasq --interface="$ETH_IF" \
                --dhcp-range=$DHCP_RANGE \
                --dhcp-option=option:router,192.168.1.101 \
                --dhcp-option=option:dns-server,8.8.8.8 \
                --no-daemon --port=0 &
        fi

        echo ""
        echo "=== 已开启 ==="
        check_running
        echo ""
        echo "开发板将自动获取 IP (192.168.1.100-200)"
        echo "SSH: ssh root@192.168.1.100"
        ;;
    off)
        echo "=== 关闭 WiFi 共享 ==="
        killall dnsmasq 2>/dev/null && echo "  dnsmasq 已停止"
        sysctl -w net.ipv4.ip_forward=0 >/dev/null
        iptables -t nat -D POSTROUTING -o "$WIFI_IF" -j MASQUERADE 2>/dev/null
        iptables -D ufw-user-forward -i "$ETH_IF" -o "$WIFI_IF" -j ACCEPT 2>/dev/null
        iptables -D ufw-user-forward -i "$WIFI_IF" -o "$ETH_IF" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null
        echo "=== 已关闭 ==="
        ;;
    status)
        echo "=== WiFi 共享状态 ==="
        check_running
        echo ""
        echo "DHCP 租约:"
        cat /var/lib/misc/dnsmasq.leases 2>/dev/null || echo "  无租约"
        ;;
    *)
        echo "用法: sudo bash $0 [on|off|status]"
        exit 1
        ;;
esac
