import socket
import struct
import time
import pandas as pd
import random

# 协议常量
SYN = 1
SYN_ACK = 2
ACK = 3
DATA = 4
FIN = 5

# 协议参数
INIT_TIMEOUT = 0.3  # 300ms
DROP_RATE = 0.2  # 20%丢包率
WINDOW_SIZE = 400  # 窗口大小400字节
PKT_SIZE = 80  # 数据包大小

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # 创建客户机socket
server_ip = input("请输入服务端IP地址：")
port = int(input("请输入端口号："))

# 连接建立过程
init = struct.pack('>HH', SYN, 0)  # SYN=1, seq=0
client_socket.sendto(init, (server_ip, port))
print("发送SYN请求")

agree = client_socket.recv(4)
agree_data, ack_num = struct.unpack('>HH', agree)
if agree_data != SYN_ACK:
    raise ValueError('连接建立失败！')
print("收到SYN-ACK响应")

established = struct.pack('>HH', ACK, ack_num + 1)  # ACK=3
client_socket.sendto(established, (server_ip, port))
print("发送ACK完成三次握手")
print("连接建立成功\n")

# 准备发送数据
f = open('send.txt', 'rb')
x = []  # 记录每块起始位置
y = []  # 记录每块结束位置
chunks_num = 0  # 数据块编号
sends = []  # 所有待发送数据

# 读取文件并打包数据
while True:
    chunk = f.read(76)  # 每块76字节(头部4字节)
    if not chunk:
        break
    send_header = struct.pack('>HH', DATA,chunks_num)  #type, seq
    chunks_num += 1
    start = (chunks_num - 1) * 76
    x.append(start)
    end = start + len(chunk)
    y.append(end)
    sends.append(send_header + chunk)
f.close()

# 初始化统计变量
rtt_list = []
start_times = []
total_packets_sent = 0
base = 0  # 窗口基序号
next_seq = 0  # 下一个发送序号
window_packets = []  # 窗口中的数据包

# 设置初始超时时间
client_socket.settimeout(INIT_TIMEOUT)

print("开始数据传输...")
while base < len(sends):
    # 发送窗口内的数据包
    while next_seq < min(base + 5, len(sends)):  # 窗口最多5个包(400字节)
        if next_seq >=base and next_seq not in window_packets:
            client_socket.sendto(sends[next_seq], (server_ip, port))
            start_times.append(time.time())
            print(f"第{next_seq}个({x[next_seq]}~{y[next_seq]}字节)client端已发送")
            total_packets_sent += 1
            window_packets.append(next_seq)
        next_seq += 1

    try:
        # 等待ACK
        back = client_socket.recv(8)
        back_type, back_ack, server_time = struct.unpack('>HhI', back)

        if back_type == ACK and back_ack >= 0:
            #计算rtt
            rtt = time.time() - start_times[back_ack]
            # 转换时间戳为 HH:MM:SS
            server_ack_time = time.strftime("%H:%M:%S", time.localtime(server_time))
            print(f"服务端发送第{back_ack}个包的ACK时间是：{server_ack_time}")

            rtt_list.append(rtt * 1000)  # 转换为毫秒
            print(f"第{back_ack}个({x[back_ack]}~{y[back_ack]}字节)包Server已收到，RTT是{rtt * 1000:.2f}ms")

            # 更新窗口基序号
            if back_ack >= base:
                base = back_ack+1
                # 从窗口中移除已确认的包
                window_packets = [seq for seq in window_packets if seq >= base]
                next_seq = base  # 允许发送新包
            # 动态调整超时时间(使用平均RTT的2倍)
            if rtt_list:
                avg_rtt = sum(rtt_list) / len(rtt_list)
                client_socket.settimeout(2 * avg_rtt / 1000)  # 转换为秒

    except socket.timeout:
        # 超时重传窗口中的所有包
        print("超时，重传窗口中所有数据包")
        for seq in window_packets:
            client_socket.sendto(sends[seq], (server_ip, port))
            start_times[seq] = time.time()  # 更新发送时间
            total_packets_sent += 1
            print(f"重传第{seq}个({x[seq]}~{y[seq]}字节)")
        # 重置next_seq以允许重新发送窗口中的包
        next_seq = base

# 传输结束，输出统计信息
print("\n传输完成，统计信息：")
print(f"总发送数据包数量: {total_packets_sent}")
print(f"实际需要的数据包数量: {len(sends)}")
loss_rate = (total_packets_sent - len(sends)) / total_packets_sent * 100
print(f"丢包率: {loss_rate:.2f}%")

if rtt_list:
    rtt_series = pd.Series(rtt_list)
    print(f"最大RTT: {rtt_series.max():.2f}ms")
    print(f"最小RTT: {rtt_series.min():.2f}ms")
    print(f"平均RTT: {rtt_series.mean():.2f}ms")
    print(f"RTT标准差: {rtt_series.std():.2f}ms")
else:
    print("没有有效的RTT数据")

# 关闭连接
fin = struct.pack('>HH', FIN, 0)
client_socket.sendto(fin, (server_ip, port))#发送关闭信号
client_socket.close()