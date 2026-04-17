import tkinter as tk
from tkinter import ttk
import serial
import threading

# === 修改這裡成你的 COM Port ===
SERIAL_PORT = "COM8"   # Windows: COMx, Linux: /dev/ttyUSB0
BAUDRATE = 115200

# 打開 UART
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)

# === 背景讀取 MCU 回覆 ===
def read_serial():
    while True:
        if ser.in_waiting:
            line = ser.readline().decode(errors="ignore").strip()
            if line:
                log_text.insert(tk.END, line + "\n")
                log_text.see(tk.END)

threading.Thread(target=read_serial, daemon=True).start()

# === 指令發送 ===
def send_command(cmd):
    ser.write((cmd + "\r\n").encode())

# === GUI 界面 ===
root = tk.Tk()
root.title("STM32 GPIO 控制面板")
root.geometry("500x400")

# Port/Pin 選擇
frm_top = ttk.Frame(root)
frm_top.pack(pady=10)

ttk.Label(frm_top, text="Port:").grid(row=0, column=0, padx=5)
port_var = tk.StringVar(value="C")
port_entry = ttk.Entry(frm_top, textvariable=port_var, width=5)
port_entry.grid(row=0, column=1)

ttk.Label(frm_top, text="Pin:").grid(row=0, column=2, padx=5)
pin_var = tk.StringVar(value="13")
pin_entry = ttk.Entry(frm_top, textvariable=pin_var, width=5)
pin_entry.grid(row=0, column=3)

# 模式設定按鈕
def set_mode(m):
    send_command(f"MODE,{port_var.get()},{pin_var.get()},{m}")

frm_mode = ttk.Frame(root)
frm_mode.pack(pady=5)
for m in ["OUT", "IN", "PU", "PD", "AN"]:
    ttk.Button(frm_mode, text=m, command=lambda mm=m: set_mode(mm)).pack(side=tk.LEFT, padx=3)

# 輸出控制
frm_write = ttk.Frame(root)
frm_write.pack(pady=5)

ttk.Button(frm_write, text="Write 1", command=lambda: send_command(f"WRITE,{port_var.get()},{pin_var.get()},1")).pack(side=tk.LEFT, padx=5)
ttk.Button(frm_write, text="Write 0", command=lambda: send_command(f"WRITE,{port_var.get()},{pin_var.get()},0")).pack(side=tk.LEFT, padx=5)

# 讀取按鈕
ttk.Button(root, text="Read Pin", command=lambda: send_command(f"READ,{port_var.get()},{pin_var.get()}")).pack(pady=5)

# Log 顯示區
log_text = tk.Text(root, height=12)
log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

root.mainloop()
