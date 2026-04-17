def crc16_ccitt(payload: bytes) -> int:
    """
    計算 CRC16-CCITT (XModem / FALSE)
    Polynomial: 0x1021
    Init: 0xFFFF
    """
    crc = 0xFFFF
    for b in payload:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def build_crc_command(payload: str) -> str:
    """
    將 payload 字串轉換成完整指令
    包含 $ 與 CRC16-CCITT
    """
    payload_bytes = payload.encode('ascii')
    crc = crc16_ccitt(payload_bytes)
    crc_str = f"{crc:04X}"  # 大寫十六進位 4 位
    return f"${payload}*{crc_str}"

if __name__ == "__main__":
    while True:
        payload = input("請輸入 payload（不要加 $ 或 *CRC）: ").strip()
        full_cmd = build_crc_command(payload)
        print(f"完整指令：{full_cmd}\n")
